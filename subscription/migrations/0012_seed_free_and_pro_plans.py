from django.db import migrations, transaction


DELETE_PACKAGE_NAMES = ["Explorer", "Career Builder", "Career Pro"]
CREATE_PLANS = [
    {
        "package_name": "Free",
        "description": "Free tier with limited access",
        "prices": [
            {"period": "yearly", "price": 0, "duration_days": 365},
        ],
    },
    {
        "package_name": "Pro",
        "description": "Pro tier with full access",
        "prices": [
            {"period": "yearly", "price": 1800, "duration_days": 365},
        ],
    },
]


def seed_plans(apps, schema_editor):
    Subscription = apps.get_model("subscription", "Subscription")
    PlanPrice = apps.get_model("subscription", "PlanPrice")

    with transaction.atomic():
        # 1. Delete old empty plans (cascade deletes their features/prices)
        Subscription.objects.filter(package_name__in=DELETE_PACKAGE_NAMES).delete()

        # 2. Create Free and Pro plans
        for plan_data in CREATE_PLANS:
            prices_data = plan_data.pop("prices")
            plan = Subscription.objects.create(**plan_data)
            for price_data in prices_data:
                PlanPrice.objects.create(plan=plan, **price_data)


def reverse_seed(apps, schema_editor):
    Subscription = apps.get_model("subscription", "Subscription")

    with transaction.atomic():
        # Delete Free and Pro plans (cascade deletes prices)
        Subscription.objects.filter(
            package_name__in=[p["package_name"] for p in CREATE_PLANS]
        ).delete()

        # Recreate old empty plans
        for name in DELETE_PACKAGE_NAMES:
            Subscription.objects.create(package_name=name, is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0011_subscriptionplan_remove_featureusage_subscription_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_plans, reverse_seed, atomic=True),
    ]
