from django.db import migrations, transaction
from django.utils.timezone import now

PLANS = [
    {
        "pk": 1,
        "package_name": "Free",
        "description": "Free tier with limited access to career assessment, internship, job assistance, and course certification features.",
        "price_pk": 1,
        "price_data": {"period": "yearly", "price": 0, "duration_days": 365},
    },
    {
        "pk": 2,
        "package_name": "Pro",
        "description": "Full access to profile assessments, unlimited internship, job, and course access, career compare, roadmap, and AI chat.",
        "price_pk": 2,
        "price_data": {"period": "yearly", "price": 1800, "duration_days": 365},
    },
]


def fix_ids(apps, schema_editor):
    Subscription = apps.get_model("subscription", "Subscription")
    PlanPrice = apps.get_model("subscription", "PlanPrice")

    with transaction.atomic():
        # Delete current Free (ID=4) and Pro (ID=5) — cascade removes their PlanPrice records
        Subscription.objects.filter(package_name__in=["Free", "Pro"]).delete()

        # Recreate with clean sequential IDs
        for plan in PLANS:
            sub = Subscription.objects.create(
                pk=plan["pk"],
                package_name=plan["package_name"],
                description=plan["description"],
                is_active=True,
                created_at=now(),
                updated_at=now(),
            )
            PlanPrice.objects.create(
                pk=plan["price_pk"],
                plan=sub,
                period=plan["price_data"]["period"],
                price=plan["price_data"]["price"],
                duration_days=plan["price_data"]["duration_days"],
                is_active=True,
                created_at=now(),
                updated_at=now(),
            )


def reverse_fix(apps, schema_editor):
    Subscription = apps.get_model("subscription", "Subscription")

    with transaction.atomic():
        # Delete Free (ID=1) and Pro (ID=2)
        Subscription.objects.filter(pk__in=[1, 2]).delete()

        # Recreate Free at ID=4 and Pro at ID=5 (original positions from 0012)
        sub_free = Subscription.objects.create(
            pk=4,
            package_name="Free",
            description="Free tier with limited access.",
            is_active=True,
        )
        apps.get_model("subscription", "PlanPrice").objects.create(
            pk=1, plan=sub_free, period="yearly", price=0, duration_days=365
        )

        sub_pro = Subscription.objects.create(
            pk=5,
            package_name="Pro",
            description="Pro tier with full access.",
            is_active=True,
        )
        apps.get_model("subscription", "PlanPrice").objects.create(
            pk=2, plan=sub_pro, period="yearly", price=1800, duration_days=365
        )


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0012_seed_free_and_pro_plans"),
    ]

    operations = [
        migrations.RunPython(fix_ids, reverse_fix, atomic=True),
    ]
