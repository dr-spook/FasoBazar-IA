"""Commande Django : python manage.py seed"""
from django.core.management.base import BaseCommand
from apps.core.services import seed_demo_data


class Command(BaseCommand):
    help = 'Charge les données de démo (5 commerçantes fictives)'

    def handle(self, *args, **options):
        seed_demo_data()
        self.stdout.write(self.style.SUCCESS('✅ Seed terminé'))