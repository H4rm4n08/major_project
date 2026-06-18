"""Overall player rating out of 100.

CricAPI's free tier only exposes career-aggregate ODI stats (runs, batting
average, strike rate, wickets, economy) — there's no ball-by-ball or
match-situation data available, so "performance under pressure" and
"consistency" can't be measured directly. Instead they're approximated using
the stats that are a reasonable real-world proxy for them:
  - batting average / economy reward players whose output doesn't collapse
    under tougher bowling/batting attacks (a stand-in for consistency)
  - strike rate and wickets reward players who can actually influence a
    result, not just accumulate numbers (a stand-in for impact under pressure)

Every player is scored as a percentile against every other player currently
in the database for each stat, so the rating is always comparative rather
than absolute, then weighted by role and adjusted by a team-strength factor
reflecting the calibre of attack/opposition that nation's players typically
face in ODIs.
"""

from .models import PlayerStats

# Rough relative ODI strength of each nation, used as a multiplier so that
# performing for a top side (facing tougher attacks, more scrutiny) counts
# for slightly more than the same raw numbers for a weaker side.
TEAM_STRENGTH = {
    "india": 1.05, "australia": 1.05, "england": 1.03,
    "new zealand": 1.02, "south africa": 1.02, "pakistan": 1.00,
    "sri lanka": 0.97, "west indies": 0.95, "bangladesh": 0.93,
    "afghanistan": 0.93, "zimbabwe": 0.85, "ireland": 0.85,
    "netherlands": 0.80, "scotland": 0.80, "nepal": 0.78,
    "usa": 0.78, "united states of america": 0.78, "uae": 0.78,
    "u.a.e.": 0.78, "oman": 0.75, "canada": 0.75, "kenya": 0.75,
    "namibia": 0.75, "papua new guinea": 0.75, "hong kong": 0.75,
    "uganda": 0.72, "bermuda": 0.72, "east africa": 0.70,
}
DEFAULT_TEAM_STRENGTH = 0.80

# Flat bonus added to all-rounders' raw score, before the team-strength
# multiplier, to account for their fielding/versatility value that isn't
# captured by any single batting or bowling stat.
ALLROUNDER_VERSATILITY_BONUS = 8


def _percentile(value, all_values, lower_is_better=False):
    """Where `value` ranks among `all_values`, as 0-100. Neutral 50 if unknown."""
    if value is None or not all_values:
        return 50
    if lower_is_better:
        rank = sum(1 for v in all_values if v >= value)
    else:
        rank = sum(1 for v in all_values if v <= value)
    return round((rank / len(all_values)) * 100)


def role_category(role_name):
    name = (role_name or "").lower()
    if "all" in name:
        return "allrounder"
    if "bowl" in name:
        return "bowler"
    return "batsman"  # covers batsman, wicketkeeper, and unknown roles


def recalculate_all_ratings():
    """Recompute overall_rating for every player, relative to the current population."""
    all_stats = list(PlayerStats.objects.select_related('player', 'player__role').all())
    if not all_stats:
        return 0

    batting_avgs = [float(s.batting_avg) for s in all_stats if s.batting_avg is not None]
    strike_rates = [float(s.strike_rate_bat) for s in all_stats if s.strike_rate_bat is not None]
    runs = [s.runs_scored for s in all_stats if s.runs_scored]
    wickets = [s.wickets_taken for s in all_stats if s.wickets_taken]
    economies = [float(s.bowling_economy) for s in all_stats if s.bowling_economy is not None]

    updated = 0
    for stats in all_stats:
        avg_pct = _percentile(float(stats.batting_avg) if stats.batting_avg is not None else None, batting_avgs)
        sr_pct = _percentile(float(stats.strike_rate_bat) if stats.strike_rate_bat is not None else None, strike_rates)
        runs_pct = _percentile(stats.runs_scored, runs)
        wkts_pct = _percentile(stats.wickets_taken, wickets)
        econ_pct = _percentile(float(stats.bowling_economy) if stats.bowling_economy is not None else None, economies, lower_is_better=True)

        batting_score = avg_pct * 0.5 + sr_pct * 0.3 + runs_pct * 0.2
        bowling_score = wkts_pct * 0.6 + econ_pct * 0.4

        role = stats.player.role.role_name if stats.player.role else ""
        category = role_category(role)
        if category == "bowler":
            raw = bowling_score
        elif category == "allrounder":
            # A straight 50/50 average punishes all-rounders unfairly: they're
            # percentile-ranked in both disciplines against specialists who
            # concentrate fully in one, so their weaker secondary skill drags
            # the average down even when their primary skill is excellent.
            # Weight toward whichever discipline they're actually strong in,
            # and add a flat bonus reflecting the extra value of being a
            # genuine dual threat (effective fielding and tactical flexibility
            # that a pure specialist doesn't offer, even though no fielding
            # stats exist to score directly).
            raw = max(batting_score, bowling_score) * 0.65 + min(batting_score, bowling_score) * 0.35 + ALLROUNDER_VERSATILITY_BONUS
        else:
            raw = batting_score

        team_factor = TEAM_STRENGTH.get((stats.player.country or "").strip().lower(), DEFAULT_TEAM_STRENGTH)
        rating = max(1, min(100, round(raw * team_factor)))

        if stats.overall_rating != rating:
            stats.overall_rating = rating
            stats.save(update_fields=['overall_rating'])
        updated += 1

    return updated
