from django.db import models
from django.contrib.auth.models import User


# ---------------------------------------------------------
# PLAYER ROLES
# ---------------------------------------------------------

class PlayerRole(models.Model):
    role_name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Player Role"
        verbose_name_plural = "Player Roles"

    def __str__(self):
        return self.role_name


# ---------------------------------------------------------
# PLAYERS
# ---------------------------------------------------------

class Player(models.Model):
    name = models.CharField(max_length=100)
    role = models.ForeignKey(
        PlayerRole,
        on_delete=models.SET_NULL,
        null=True,
        related_name="players"
    )
    country = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# PLAYER STATS (1-to-1)
# ---------------------------------------------------------

class PlayerStats(models.Model):
    player = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="stats"
    )
    runs_scored = models.IntegerField(default=0)
    batting_avg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    strike_rate_bat = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    wickets_taken = models.IntegerField(default=0)
    bowling_economy = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Stats for {self.player.name}"


# ---------------------------------------------------------
# COACHES
# ---------------------------------------------------------

class Coach(models.Model):
    name = models.CharField(max_length=100)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_former_player = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# SQUADS
# ---------------------------------------------------------

class Squad(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="squads"
    )
    squad_name = models.CharField(max_length=100)
    coach = models.ForeignKey(
        Coach,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coached_squads"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.squad_name


# ---------------------------------------------------------
# SQUAD PLAYERS (junction table)
# ---------------------------------------------------------

class SquadPlayer(models.Model):
    squad = models.ForeignKey(
        Squad,
        on_delete=models.CASCADE,
        related_name="players"
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="squad_memberships"
    )
    batting_order = models.PositiveSmallIntegerField(null=True, blank=True)
    is_captain = models.BooleanField(default=False)
    is_wicketkeeper = models.BooleanField(default=False)
    is_substitute = models.BooleanField(default=False)

    class Meta:
        ordering = ["batting_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["squad", "player"],
                name="unique_player_per_squad"
            ),
            models.UniqueConstraint(
                fields=["squad", "batting_order"],
                name="unique_batting_order_per_squad",
                condition=models.Q(is_substitute=False)
            ),
        ]

    def __str__(self):
        return f"{self.player.name} in {self.squad.squad_name}"
