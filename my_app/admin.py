from django.contrib import admin
from .models import PlayerRole, Player, PlayerStats, Coach, Squad, SquadPlayer


# ---------------------------------------------------------
# INLINES
# ---------------------------------------------------------

class PlayerStatsInline(admin.StackedInline):
    """Embeds the 1-to-1 stats directly inside the Player admin page."""
    model = PlayerStats
    can_delete = False
    verbose_name_plural = "Player Performance Statistics"


class SquadPlayerInline(admin.TabularInline):
    """Allows managing team members directly from the Squad admin page."""
    model = SquadPlayer
    extra = 11  # Defaults to 11 empty slots (standard cricket/football squad size)
    autocomplete_fields = ["player"]  # Requires search_fields on PlayerAdmin


# ---------------------------------------------------------
# MODEL ADMINS
# ---------------------------------------------------------

@admin.register(PlayerRole)
class PlayerRoleAdmin(admin.ModelAdmin):
    list_display = ["id", "role_name"]
    search_fields = ["role_name"]


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "role", "country", "bowling_pace", "bowling_spin_type", "get_runs", "get_wickets"]
    list_filter = ["role", "country", "bowling_pace", "bowling_spin_type"]
    search_fields = ["name", "country"]
    inlines = [PlayerStatsInline]

    # Custom methods to safely pull 1-to-1 statistics into the list view
    @admin.display(ordering="stats__runs_scored", description="Runs")
    def get_runs(self, obj):
        try:
            return obj.stats.runs_scored
        except PlayerStats.DoesNotExist:
            return 0

    @admin.display(ordering="stats__wickets_taken", description="Wickets")
    def get_wickets(self, obj):
        try:
            return obj.stats.wickets_taken
        except PlayerStats.DoesNotExist:
            return 0


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ["name", "win_rate", "is_former_player"]
    list_filter = ["is_former_player"]
    search_fields = ["name"]


@admin.register(Squad)
class SquadAdmin(admin.ModelAdmin):
    list_display = ["squad_name", "user", "coach", "created_at"]
    list_filter = ["coach", "created_at", "user"]
    search_fields = ["squad_name", "user__username"]
    autocomplete_fields = ["user", "coach"]  # Clean dropdowns for high volume datasets
    date_hierarchy = "created_at"
    inlines = [SquadPlayerInline]


@admin.register(SquadPlayer)
class SquadPlayerAdmin(admin.ModelAdmin):
    """
    Optional standalone admin for deep analytical filtering of team roles
    across all instances.
    """
    list_display = [
        "squad", 
        "player", 
        "batting_order", 
        "is_captain", 
        "is_wicketkeeper", 
        "is_substitute"
    ]
    list_filter = ["is_captain", "is_wicketkeeper", "is_substitute", "squad"]
    search_fields = ["squad__squad_name", "player__name"]
    autocomplete_fields = ["squad", "player"]

from .models import LiveScoreCache, FixtureCache, PlayerStatsCache


@admin.register(LiveScoreCache)
class LiveScoreCacheAdmin(admin.ModelAdmin):
    list_display = ["match_id", "fetched_at"]
    readonly_fields = ["match_id", "data", "fetched_at"]


@admin.register(FixtureCache)
class FixtureCacheAdmin(admin.ModelAdmin):
    list_display = ["match_id", "fetched_at"]
    readonly_fields = ["match_id", "data", "fetched_at"]


@admin.register(PlayerStatsCache)
class PlayerStatsCacheAdmin(admin.ModelAdmin):
    list_display = ["player_id", "fetched_at"]
    readonly_fields = ["player_id", "data", "fetched_at"]


from .models import PlayerSyncState


@admin.register(PlayerSyncState)
class PlayerSyncStateAdmin(admin.ModelAdmin):
    list_display = ["last_offset", "updated_at"]
    readonly_fields = ["last_offset", "updated_at"]
