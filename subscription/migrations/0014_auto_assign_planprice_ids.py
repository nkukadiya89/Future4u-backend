from django.db import migrations, transaction
from django.utils.timezone import now

PLANS = [
    {
        "package_name": "Free",
        "description": "Free tier with limited access to career assessment, internship, job assistance, and course certification features.",
        "price_data": {"period": "yearly", "price": 0, "duration_days": 365},
    },
    {
        "package_name": "Pro",
        "description": "Full access to profile assessments, unlimited internship, job, and course access, career compare, roadmap, and AI chat.",
        "price_data": {"period": "yearly", "price": 1800, "duration_days": 365},
    },
]


def seed_plans(apps, schema_editor):
    Subscription = apps.get_model("subscription", "Subscription")
    PlanPrice = apps.get_model("subscription", "PlanPrice")

    with transaction.atomic():
        for plan in PLANS:
            # Use update_or_create to avoid duplicate key errors
            sub, created = Subscription.objects.update_or_create(
                package_name=plan["package_name"],
                defaults={
                    "description": plan["description"],
                    "is_active": True,
                    "updated_at": now(),
                },
            )
            if created:
                sub.created_at = now()
                sub.save(update_fields=["created_at"])

            # Create PlanPrice with auto-assigned ID
            PlanPrice.objects.update_or_create(
                plan=sub,
                period=plan["price_data"]["period"],
                defaults={
                    "price": plan["price_data"]["price"],
                    "duration_days": plan["price_data"]["duration_days"],
                    "is_active": True,
                    "updated_at": now(),
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0013_fix_plan_ids"),
    ]

    operations = [
        migrations.RunPython(seed_plans, migrations.RunPython.noop, atomic=True),
    ]
