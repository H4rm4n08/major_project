from decimal import Decimal, InvalidOperation
import requests
from django.conf import settings
from .models import LiveScoreCache, FixtureCache, PlayerStatsCache, Player, PlayerRole, PlayerStats

BASE_URL = "https://api.cricapi.com/v1"


def _get(endpoint, **params):
    params["apikey"] = settings.CRICAPI_KEY
    try:
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            return data.get("data", [])
    except Exception:
        pass
    return []


def get_live_scores():
    if LiveScoreCache.is_fresh():
        return LiveScoreCache.all_data()

    results = _get("cricScore")
    if results:
        for match in results:
            match_id = match.get("id") or match.get("unique_id") or str(match)
            LiveScoreCache.objects.update_or_create(
                match_id=match_id,
                defaults={"data": match},
            )
        # Remove stale entries not in this fetch
        fresh_ids = [m.get("id") or m.get("unique_id") or str(m) for m in results]
        LiveScoreCache.objects.exclude(match_id__in=fresh_ids).delete()

    return LiveScoreCache.all_data()


def get_fixtures():
    if FixtureCache.is_fresh():
        return FixtureCache.all_data()

    results = _get("matches", offset=0)
    if results:
        for match in results:
            match_id = match.get("id") or match.get("unique_id") or str(match)
            FixtureCache.objects.update_or_create(
                match_id=match_id,
                defaults={"data": match},
            )
        fresh_ids = [m.get("id") or m.get("unique_id") or str(m) for m in results]
        FixtureCache.objects.exclude(match_id__in=fresh_ids).delete()

    return FixtureCache.all_data()


def get_player_stats(player_id):
    if PlayerStatsCache.is_fresh(player_id):
        try:
            return PlayerStatsCache.objects.get(player_id=player_id).data
        except PlayerStatsCache.DoesNotExist:
            pass

    result = _get("players_info", id=player_id)
    if result and isinstance(result, dict):
        PlayerStatsCache.objects.update_or_create(
            player_id=player_id,
            defaults={"data": result},
        )
        return result

    # Fallback: return whatever is in DB even if stale
    try:
        return PlayerStatsCache.objects.get(player_id=player_id).data
    except PlayerStatsCache.DoesNotExist:
        return {}


def search_players(name):
    return _get("players", search=name, offset=0)


def get_players_page(offset):
    """Fetch one page of the full global player list (no search filter)."""
    return _get("players", offset=offset)


def _find_stat(stats_list, fn_name, matchtype, stat_key):
    """Look up a single stat value from CricAPI's stats array.

    Each entry looks like {"fn": "batting", "matchtype": "odi", "stat": "runs", "value": "13911"}.
    Some entries have whitespace-padded "matchtype"/"stat" values, so strip before comparing.
    """
    if not isinstance(stats_list, list):
        return None
    for entry in stats_list:
        if (
            str(entry.get("fn", "")).strip().lower() == fn_name
            and str(entry.get("matchtype", "")).strip().lower() == matchtype
            and str(entry.get("stat", "")).strip().lower() == stat_key
            and entry.get("value") not in (None, "", "-")
        ):
            return entry.get("value")
    return None


def has_odi_stats(stats_list):
    """True only if the player has actually played at least one ODI match.

    CricAPI returns a zeroed-out ODI stats template (matches played = "0") for
    players who've never played one, so checking for the matchtype's presence
    alone isn't enough — the "m" (matches) stat must be a positive number.
    """
    if not isinstance(stats_list, list):
        return False
    for entry in stats_list:
        if (
            str(entry.get("matchtype", "")).strip().lower() == "odi"
            and str(entry.get("stat", "")).strip().lower() == "m"
        ):
            try:
                if int(float(entry.get("value", 0))) > 0:
                    return True
            except (TypeError, ValueError):
                continue
    return False


def is_male_player(country):
    return "women" not in (country or "").lower()


# Nations that have ever held ODI status. Used to skip namesakes from
# domestic/club teams or non-cricketing countries before spending an API call
# on a stats lookup for them.
ODI_NATIONS = {
    "india", "australia", "england", "pakistan", "south africa", "new zealand",
    "sri lanka", "bangladesh", "west indies", "afghanistan", "zimbabwe", "ireland",
    "netherlands", "scotland", "u.a.e.", "uae", "oman", "nepal", "usa",
    "united states of america", "canada", "kenya", "namibia", "papua new guinea",
    "hong kong", "uganda", "bermuda", "east africa",
}


def is_likely_odi_nation(country):
    return (country or "").strip().lower() in ODI_NATIONS


def classify_bowling_style(bowling_style):
    """Parse CricAPI's free-text bowlingStyle (e.g. "Right-arm medium",
    "Legbreak googly", "Slow left-arm orthodox") into (pace, spin_type).

    pace is one of "fast"/"medium"/"spin", or None if the player doesn't
    bowl / style is unknown. spin_type is only set when pace == "spin".
    """
    style = (bowling_style or "").strip().lower()
    if not style:
        return None, None

    has_leg = any(term in style for term in ("leg break", "legbreak", "leg-break", "googly", "wrist spin", "chinaman"))
    has_off = any(term in style for term in ("off break", "offbreak", "off-break", "orthodox", "finger spin"))

    if has_leg and has_off:
        return "spin", "both"
    if has_leg:
        return "spin", "leg"
    if has_off:
        return "spin", "off"
    if "spin" in style:
        return "spin", None
    if "fast" in style:
        return "fast", None
    if "medium" in style:
        return "medium", None
    return None, None


def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _to_decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (TypeError, ValueError, InvalidOperation):
        return None


def sync_player_to_db(player_id, data):
    """Persist CricAPI player data into the relational Player/PlayerStats tables.

    Only keeps male players with recorded ODI stats — returns None (and stores
    nothing) for women's players or players with no ODI record.
    """
    if not data or not isinstance(data, dict):
        return None

    country = data.get("country") or ""
    if not is_male_player(country):
        return None

    stats_list = data.get("stats", [])
    if not has_odi_stats(stats_list):
        return None

    name = data.get("name") or "Unknown Player"
    role_name = data.get("role") or "Unknown"
    pace, spin_type = classify_bowling_style(data.get("bowlingStyle"))

    role, _ = PlayerRole.objects.get_or_create(role_name=role_name)
    player, _ = Player.objects.update_or_create(
        cricapi_id=player_id,
        defaults={
            "name": name, "country": country, "role": role,
            "bowling_pace": pace, "bowling_spin_type": spin_type,
        },
    )

    PlayerStats.objects.update_or_create(
        player=player,
        defaults={
            "runs_scored": _to_int(_find_stat(stats_list, "batting", "odi", "runs")),
            "batting_avg": _to_decimal(_find_stat(stats_list, "batting", "odi", "avg")),
            "strike_rate_bat": _to_decimal(_find_stat(stats_list, "batting", "odi", "sr")),
            "wickets_taken": _to_int(_find_stat(stats_list, "bowling", "odi", "wkts")),
            "bowling_economy": _to_decimal(_find_stat(stats_list, "bowling", "odi", "econ")),
        },
    )
    return player
