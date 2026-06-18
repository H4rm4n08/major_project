from django.core.management.base import BaseCommand
from my_app import ratings


class Command(BaseCommand):
    help = "Recompute the overall_rating (out of 100) for every player, relative to the current database."

    def handle(self, *args, **options):
        updated = ratings.recalculate_all_ratings()
        self.stdout.write(self.style.SUCCESS(f"Recalculated ratings for {updated} players."))
