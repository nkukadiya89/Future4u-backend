from django.conf import settings
from django.db import models

from common.models import BaseModule


class BusinessCategory(BaseModule):
    business_category = models.CharField(max_length=100)

    def __str__(self):
        return self.business_category

    class Meta:
        db_table = "business_category"
