from django.core.management.base import BaseCommand
from my_app.models import Player, PlayerSyncState
from my_app import cricapi_service, ratings

# Surnames of well-known male ODI internationals, current and past, across the
# major cricketing nations. CricAPI's free-tier player database has ~17,000
# entries that are mostly domestic/minor-league players with no ODI record, so
# a blind alphabet-letter search mostly misses. Searching by these names
# reliably surfaces real internationals with ODI stats instead.
SEARCH_TERMS = [
    # current/recent
    "Kohli", "Sharma", "Rahul", "Pant", "Iyer", "Gill", "Jadeja", "Ashwin", "Bumrah", "Pandya",
    "Babar", "Rizwan", "Shaheen", "Shadab", "Imam", "Fakhar",
    "Williamson", "Conway", "Mitchell", "Latham", "Phillips", "Boult", "Southee",
    "Smith", "Warner", "Maxwell", "Marsh", "Starc", "Cummins", "Hazlewood", "Head",
    "Root", "Stokes", "Buttler", "Bairstow", "Malan", "Curran", "Archer", "Wood",
    "Bavuma", "Markram", "Klaasen", "Miller", "Rabada", "Ngidi", "de Kock",
    "Shakib", "Mahmudullah", "Tamim", "Litton", "Mushfiqur", "Mustafizur",
    "Hasaranga", "Mendis", "Mathews", "Karunaratne",
    "Rashid", "Mujeeb", "Naveen", "Gurbaz", "Nabi",
    # past/retired greats
    "Tendulkar", "Dravid", "Ganguly", "Dhoni", "Sehwag", "Yuvraj", "Kumble", "Zaheer",
    "Ponting", "Gilchrist", "Warne", "McGrath", "Waugh", "Hayden", "Lee", "Symonds",
    "Akram", "Miandad", "Inzamam", "Younis", "Afridi", "Akhtar", "Malik",
    "Lara", "Richards", "Gayle", "Sobers", "Chanderpaul", "Ambrose",
    "Vaughan", "Flintoff", "Pietersen", "Trescothick", "Anderson", "Broad",
    "Jayasuriya", "Sangakkara", "Muralitharan", "Dilshan", "Malinga",
    "Crowe", "Fleming", "McCullum", "Vettori",
    "Kallis", "Pollock", "Smith", "Steyn", "de Villiers", "Amla",
]


class Command(BaseCommand):
    help = (
        "Sync male ODI players and stats from CricAPI into the database, searching by "
        "known international surnames (the unfiltered/alphabet-letter player search is "
        "dominated by minor/domestic players with no ODI record on the free tier, so "
        "name search is a far more reliable source). Resumes from the last term "
        "searched, so running this daily gradually builds coverage without exceeding "
        "the API's daily request budget."
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
        term_index = state.last_offset % len(SEARCH_TERMS)
        synced = 0
        api_calls = 0

        self.stdout.write(f"Resuming from '{SEARCH_TERMS[term_index]}', budget {limit} API calls this run.")

        while api_calls < limit:
            term = SEARCH_TERMS[term_index]
            results = cricapi_service.search_players(term)
            api_calls += 1

            for entry in results:
                if api_calls >= limit:
                    break

                player_id = entry.get("id")
                if not player_id or Player.objects.filter(cricapi_id=player_id).exists():
                    continue

                # Skip namesakes from clubs/counties/non-cricketing countries
                # without spending a stats-lookup call on them.
                if not cricapi_service.is_likely_odi_nation(entry.get("country")):
                    continue

                stats = cricapi_service.get_player_stats(player_id)
                api_calls += 1
                player = cricapi_service.sync_player_to_db(player_id, stats)
                if player:
                    synced += 1
                    self.stdout.write(f"  synced: {player.name} ({player.country})")

            term_index = (term_index + 1) % len(SEARCH_TERMS)
            state.last_offset = term_index
            state.save()

            if term_index == 0:
                self.stdout.write("Cycled through all search terms — looping back to the start next run.")
                break

        if synced:
            ratings.recalculate_all_ratings()

        self.stdout.write(self.style.SUCCESS(
            f"Done. Synced {synced} new male ODI players using ~{api_calls} API calls. "
            f"Next run resumes from '{SEARCH_TERMS[term_index]}'."
        ))
