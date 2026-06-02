from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("assessment", "0026_remove_static_recommendation_models"),
        ("domain_skill_mapping", "0005_remove_legacy_domain_skill_mapping"),
        ("jobs", "0005_remove_jobpreference_soft_skills"),
        ("skill", "0003_alter_skill_updated_at"),
        ("user_profile", "0040_delete_internshipprofileskill"),
        ("user_skill", "0003_remove_legacy_user_skill"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SkillImportError",
        ),
        migrations.DeleteModel(
            name="SkillImportBatch",
        ),
        migrations.DeleteModel(
            name="Skill",
        ),
    ]
