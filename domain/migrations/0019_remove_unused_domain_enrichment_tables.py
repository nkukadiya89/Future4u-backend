from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0018_alter_domain_updated_at"),
    ]

    operations = [
        migrations.DeleteModel(
            name="DomainScoringConfig",
        ),
        migrations.DeleteModel(
            name="DomainCounsellorKnowledge",
        ),
        migrations.DeleteModel(
            name="DomainReportMeta",
        ),
        migrations.DeleteModel(
            name="StreamCounsellorKnowledge",
        ),
        migrations.DeleteModel(
            name="StreamReportMeta",
        ),
    ]
