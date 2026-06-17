from django.core.management.base import BaseCommand
from my_app.models import Player, PlayerSyncState
from my_app import cricapi_service

LETTERS = "abcdefghijklmnopqrstuvwxyz"


class Command(BaseCommand):
    help = (
        "Sync male ODI players and stats from CricAPI into the database, searching "
        "name-by-letter (the unfiltered full player list is dominated by minor/women's "
        "domestic players on the free tier, so search is a better source of internationals). "
        "Resumes from the last letter searched, so running this daily gradually builds "
        "coverage without exceeding the API's daily request budget."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=80,
            help="Max number of API calls to spend this run (search + per-player lookups).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        state, _ = PlayerSyncState.objects.get_or_create(pk=1)
        letter_index = state.last_offset % len(LETTERS)
        synced = 0
        api_calls = 0

        self.stdout.write(f"Resuming from letter '{LETTERS[letter_index]}', budget {limit} API calls this run.")

        while api_calls < limit:
            letter = LETTERS[letter_index]
            results = cricapi_service.search_players(letter)
            api_calls += 1

            for entry in results:
                if api_calls >= limit:
                    break

                player_id = entry.get("id")
                if not player_id or Player.objects.filter(cricapi_id=player_id).exists():
                    continue

                stats = cricapi_service.get_player_stats(player_id)
                api_calls += 1
                player = cricapi_service.sync_player_to_db(player_id, stats)
                if player:
                    synced += 1
                    self.stdout.write(f"  synced: {player.name} ({player.country})")

            letter_index = (letter_index + 1) % len(LETTERS)
            state.last_offset = letter_index
            state.save()

        self.stdout.write(self.style.SUCCESS(
            f"Done. Synced {synced} new male ODI players using ~{api_calls} API calls. "
            f"Next run resumes from letter '{LETTERS[letter_index]}'."
        ))
