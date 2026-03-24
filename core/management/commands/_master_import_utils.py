import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

User = get_user_model()


class RequestUserProxy:
    __slots__ = ("user",)

    def __init__(self, user):
        self.user = user


def resolve_import_user(*, username: str | None):
    user = None
    if username:
        user = User.objects.filter(username=username).first()
        if not user:
            raise CommandError(f"User not found: {username}")
    if user is None:
        user = User.objects.filter(is_superuser=True).first() or User.objects.order_by("pk").first()
    if user is None:
        raise CommandError("No user available for audit fields; create a user or pass --username.")
    return user


def load_csv_rows(file_path: str) -> list[dict]:
    path = Path(file_path)
    if not path.is_file():
        raise CommandError(f"File not found: {path}")
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise CommandError("CSV has no header row.")
        for row in reader:
            if not any((v or "").strip() for v in row.values()):
                continue
            rows.append(dict(row))
    if not rows:
        raise CommandError("No data rows in CSV.")
    return rows

