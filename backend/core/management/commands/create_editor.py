import os
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from core.portfolio import EDITOR_PERMISSIONS, CATEGORY_PERMISSIONS
from core.lead_cabinet import BUSINESS_PERMISSIONS

class Command(BaseCommand):
    help = "Create a portfolio editor using VLICO_EDITOR_PASSWORD from the environment; never prints a password."
    def add_arguments(self, parser):
        parser.add_argument("--username", default="vlico")
    def handle(self, *args, **options):
        username = options["username"]
        if get_user_model().objects.filter(username=username).exists():
            self.stdout.write("Account already exists; credentials and permissions preserved.")
            return
        password = os.environ.get("VLICO_EDITOR_PASSWORD", "")
        if not password:
            raise CommandError("Set VLICO_EDITOR_PASSWORD privately in the environment first.")
        validate_password(password)
        group, _ = Group.objects.get_or_create(name="Portfolio editors")
        group.permissions.add(*Permission.objects.filter(content_type__app_label="core", codename__in=[p.split(".")[1] for p in EDITOR_PERMISSIONS + CATEGORY_PERMISSIONS + BUSINESS_PERMISSIONS]))
        user = get_user_model().objects.create_user(username=username, password=password, is_staff=True)
        user.groups.add(group)
        self.stdout.write("Portfolio editor created. Password was not displayed.")
