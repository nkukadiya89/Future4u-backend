from django.db import migrations


def remove_seeded_features(apps, schema_editor):
    """Remove all SubscriptionFeature records seeded by migration 0015."""
    SubscriptionFeature = apps.get_model("subscription", "SubscriptionFeature")
    deleted, _ = SubscriptionFeature.objects.filter(
        subscription__package_name__in=["Free", "Pro"],
    ).delete()
    if deleted:
        print(f"Removed {deleted} seeded feature(s) from Free/Pro plans")


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0015_seed_plan_features_and_last_reset"),
    ]

    operations = [
        migrations.RunPython(remove_seeded_features, atomic=True),
    ]
