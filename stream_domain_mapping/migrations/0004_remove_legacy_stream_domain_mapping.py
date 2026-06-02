from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("stream_domain_mapping", "0003_alter_streamdomainmapping_updated_at"),
    ]

    operations = [
        migrations.DeleteModel(name="StreamDomainMappingImportError"),
        migrations.DeleteModel(name="StreamDomainMappingImportBatch"),
        migrations.DeleteModel(name="StreamDomainMapping"),
    ]
