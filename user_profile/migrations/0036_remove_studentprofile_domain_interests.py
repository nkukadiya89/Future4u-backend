from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0035_studentprofile_domain_interests"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="studentprofile",
            name="domain_interests",
        ),
    ]
