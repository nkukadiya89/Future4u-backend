from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("career", "0003_alter_career_updated_at"),
        ("domain_career_mapping", "0004_remove_legacy_domain_career_mapping"),
    ]

    operations = [
        migrations.DeleteModel(name="CareerImportError"),
        migrations.DeleteModel(name="CareerImportBatch"),
        migrations.DeleteModel(name="Career"),
    ]
