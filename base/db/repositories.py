from django.db import transaction


class BaseRepository:
    @staticmethod
    def atomic():
        return transaction.atomic()
