from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from base.models import BaseModel


class UserSkill(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_skills",
    )
    skill = models.ForeignKey(
        "skill.Skill",
        on_delete=models.CASCADE,
        related_name="user_skills",
    )
    proficiency_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        db_table = "user_skill"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "skill"],
                name="user_skill_user_skill_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(proficiency_score__gte=0) & models.Q(proficiency_score__lte=100),
                name="user_skill_proficiency_0_100_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["skill"]),
            models.Index(fields=["proficiency_score"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deleted"]),
        ]
        ordering = ["-updated_at", "id"]

    def __str__(self):
        return f"user={self.user_id}, skill={self.skill_id}, score={self.proficiency_score}"
