from django.db import migrations, models
from django.utils.timezone import now

# Seed data matching core/management/commands/init_data.py
PLAN_FEATURES = {
    "Free": {
        "subscription_feature": [
            {
                "feature_name": "Single Profile Assessment",
                "feature_status": True,
                "feature_code": "assessment",
                "value": "1",
                "is_unlimited": False,
            },
            {
                "feature_name": "Limited Internship Access",
                "feature_status": True,
                "feature_code": "internship",
                "value": "3",
                "is_unlimited": False,
            },
            {
                "feature_name": "Limited Job Assistance",
                "feature_status": True,
                "feature_code": "job",
                "value": "3",
                "is_unlimited": False,
            },
            {
                "feature_name": "Limited Course Certification",
                "feature_status": True,
                "feature_code": "course",
                "value": "3",
                "is_unlimited": False,
            },
            {
                "feature_name": "Career Compare",
                "feature_status": False,
                "feature_code": "career_compare",
                "is_unlimited": False,
            },
            {
                "feature_name": "Monthly Token Allowance",
                "feature_status": True,
                "feature_code": "monthly_tokens",
                "value": "10000",
                "is_unlimited": False,
            },
            {
                "feature_name": "Course Generation",
                "feature_status": True,
                "feature_code": "course_gen",
                "value": "3",
                "is_unlimited": False,
            },
            {
                "feature_name": "Internship Generation",
                "feature_status": True,
                "feature_code": "internship_gen",
                "value": "3",
                "is_unlimited": False,
            },
            {
                "feature_name": "Job Generation",
                "feature_status": True,
                "feature_code": "job_gen",
                "value": "3",
                "is_unlimited": False,
            },
            {
                "feature_name": "Resume Enhancement",
                "feature_status": True,
                "feature_code": "resume_enhance",
                "value": "1",
                "is_unlimited": False,
            },
            {
                "feature_name": "AI Chat",
                "feature_status": True,
                "feature_code": "ai_chat",
                "value": "5",
                "is_unlimited": False,
            },
        ],
    },
    "Pro": {
        "subscription_feature": [
            {
                "feature_name": "Profile Assessments",
                "feature_status": True,
                "feature_code": "assessment",
                "value": "3",
                "is_unlimited": False,
            },
            {
                "feature_name": "Full Internship Access",
                "feature_status": True,
                "feature_code": "internship",
                "is_unlimited": True,
            },
            {
                "feature_name": "Full Job Assistance",
                "feature_status": True,
                "feature_code": "job",
                "is_unlimited": True,
            },
            {
                "feature_name": "Full Course Certification",
                "feature_status": True,
                "feature_code": "course",
                "is_unlimited": True,
            },
            {
                "feature_name": "Career Compare",
                "feature_status": True,
                "feature_code": "career_compare",
                "is_unlimited": True,
            },
            {
                "feature_name": "AI Chat Access",
                "feature_status": True,
                "feature_code": "ai_chat",
                "is_unlimited": True,
            },
            {
                "feature_name": "Monthly Token Allowance",
                "feature_status": True,
                "feature_code": "monthly_tokens",
                "value": "30000",
                "is_unlimited": False,
            },
            {
                "feature_name": "Course Generation",
                "feature_status": True,
                "feature_code": "course_gen",
                "is_unlimited": True,
            },
            {
                "feature_name": "Internship Generation",
                "feature_status": True,
                "feature_code": "internship_gen",
                "is_unlimited": True,
            },
            {
                "feature_name": "Job Generation",
                "feature_status": True,
                "feature_code": "job_gen",
                "is_unlimited": True,
            },
            {
                "feature_name": "Resume Enhancement",
                "feature_status": True,
                "feature_code": "resume_enhance",
                "is_unlimited": True,
            },
        ],
    },
}


def seed_plan_features(apps, schema_editor):
    Subscription = apps.get_model("subscription", "Subscription")
    SubscriptionFeature = apps.get_model("subscription", "SubscriptionFeature")

    for package_name, plan_data in PLAN_FEATURES.items():
        plan = Subscription.objects.filter(
            package_name__iexact=package_name,
            deleted=False,
        ).first()
        if not plan:
            continue

        for feat in plan_data["subscription_feature"]:
            SubscriptionFeature.objects.update_or_create(
                subscription=plan,
                feature_name=feat["feature_name"],
                defaults={
                    "feature_code": feat.get("feature_code"),
                    "value": feat.get("value"),
                    "is_unlimited": feat.get("is_unlimited", False),
                    "is_enabled": feat["feature_status"],
                    "is_core": False,
                },
            )


def reverse_seed(apps, schema_editor):
    """Reverse is a no-op — removing feature data could break the system."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0014_auto_assign_planprice_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersubscription",
            name="last_reset_at",
            field=models.DateField(null=True, blank=True),
        ),
        migrations.RunPython(seed_plan_features, reverse_seed, atomic=True),
    ]
