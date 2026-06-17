import requests
from django.conf import settings
from .models import LiveScoreCache, FixtureCache, PlayerStatsCache

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
