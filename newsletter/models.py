from django.conf import settings
from django.db import models
from django.utils.timezone import now

# Create your models here.


class NewsLetter(models.Model):
    email = models.EmailField()
    subscribe = models.BooleanField(default=False)
    unsubscribe_reason = models.CharField(max_length=150)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="news_letter_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="news_letter_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.email}"

    class Meta:
        db_table = "news_letter"
