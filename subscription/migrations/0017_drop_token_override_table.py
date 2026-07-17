from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0016_remove_seeded_plan_features"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS token_override CASCADE",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
