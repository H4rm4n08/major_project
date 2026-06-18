import random
from django.core.management.base import BaseCommand
from my_app.models import Player, PlayerRole, PlayerStats
from my_app import ratings

FIRST_NAMES = [
    "James", "Liam", "Noah", "Oliver", "Ethan", "Lucas", "Mason", "Logan", "Henry", "Jack",
    "Daniel", "Ryan", "Aiden", "Caleb", "Nathan", "Adam", "Joel", "Mark", "Steven", "Brian",
    "Arjun", "Rohan", "Vikram", "Karan", "Aditya", "Imran", "Wasim", "Shahid", "Yusuf", "Tariq",
    "Trent", "Marcus", "Lewis", "Connor", "Harry", "George", "Tom", "Sam", "Ben", "Josh",
    "Riley", "Cameron", "Dylan", "Blake", "Tyler", "Cole", "Reece", "Owen", "Finn", "Theo",
]

COUNTRIES = ["India", "Australia", "England", "Pakistan", "South Africa", "New Zealand",
             "Sri Lanka", "Bangladesh", "West Indies", "Afghanistan"]

ROLES = ["Batsman", "Bowler", "All-rounder", "Wicketkeeper"]

BOWLING_STYLES = [
    ("fast", None), ("medium", None),
    ("spin", "leg"), ("spin", "off"),
]


class Command(BaseCommand):
    help = "Seed the database with dummy male ODI international players and stats, for testing the squad-builder UI without touching the CricAPI quota."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=50)

    def handle(self, *args, **options):
        count = options["count"]
        created = 0

        for i in range(count):
            first = FIRST_NAMES[i % len(FIRST_NAMES)]
            surname = f"Player{i+1}"
            name = f"{first} {surname}"
            country = COUNTRIES[i % len(COUNTRIES)]
            role_name = ROLES[i % len(ROLES)]
            cricapi_id = f"dummy-{i+1:03d}"

            pace, spin_type = (None, None)
            if role_name in ("Bowler", "All-rounder"):
                pace, spin_type = BOWLING_STYLES[i % len(BOWLING_STYLES)]

            role, _ = PlayerRole.objects.get_or_create(role_name=role_name)
            player, _ = Player.objects.update_or_create(
                cricapi_id=cricapi_id,
                defaults={
                    "name": name, "country": country, "role": role,
                    "bowling_pace": pace, "bowling_spin_type": spin_type,
                },
            )

            if role_name == "Bowler":
                runs, avg, sr = random.randint(50, 800), round(random.uniform(8, 20), 2), round(random.uniform(60, 90), 2)
                wkts, econ = random.randint(80, 250), round(random.uniform(3.5, 5.5), 2)
            elif role_name == "All-rounder":
                runs, avg, sr = random.randint(1500, 4000), round(random.uniform(25, 40), 2), round(random.uniform(75, 100), 2)
                wkts, econ = random.randint(50, 150), round(random.uniform(4.0, 5.5), 2)
            elif role_name == "Wicketkeeper":
                runs, avg, sr = random.randint(2000, 6000), round(random.uniform(30, 50), 2), round(random.uniform(80, 110), 2)
                wkts, econ = 0, None
            else:  # Batsman
                runs, avg, sr = random.randint(3000, 12000), round(random.uniform(35, 58), 2), round(random.uniform(80, 100), 2)
                wkts, econ = 0, None

            PlayerStats.objects.update_or_create(
                player=player,
                defaults={
                    "runs_scored": runs,
                    "batting_avg": avg,
                    "strike_rate_bat": sr,
                    "wickets_taken": wkts,
                    "bowling_economy": econ,
                },
            )
            created += 1
            self.stdout.write(f"  seeded: {name} ({country}, {role_name})")

        ratings.recalculate_all_ratings()
        self.stdout.write(self.style.SUCCESS(f"Done. Seeded {created} dummy male ODI players."))
