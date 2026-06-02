from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("user_skill", "0002_alter_userskill_updated_at"),
    ]

    operations = [
        migrations.DeleteModel(
            name="UserSkill",
        ),
    ]
