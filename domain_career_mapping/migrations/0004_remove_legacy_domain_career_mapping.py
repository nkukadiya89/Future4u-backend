from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("domain_career_mapping", "0003_alter_domaincareermapping_updated_at"),
    ]

    operations = [
        migrations.DeleteModel(name="DomainCareerMappingImportError"),
        migrations.DeleteModel(name="DomainCareerMappingImportBatch"),
        migrations.DeleteModel(name="DomainCareerMapping"),
    ]
