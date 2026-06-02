from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("domain_skill_mapping", "0004_alter_domainskillmapping_updated_at"),
    ]

    operations = [
        migrations.DeleteModel(name="DomainSkillMappingImportError"),
        migrations.DeleteModel(name="DomainSkillMappingImportBatch"),
        migrations.DeleteModel(name="DomainSkillMapping"),
    ]
