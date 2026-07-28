"""
Management command to create a free test subscription for the
personal project recommendation feature.

Usage:
    python manage.py setup_test_subscription --email student@example.com
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from subscription.models import (
    PlanPrice,
    Subscription,
    SubscriptionFeature,
    UserSubscription,
)
from user.models import User


class Command(BaseCommand):
    help = "Create a free test subscription with tokens for a test user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email of the user to assign the free subscription to",
        )

    def handle(self, *args, **options):
        email = options["email"].strip()

        user = User.objects.filter(email=email).first()
        if not user:
            raise CommandError(f"User with email '{email}' not found")

        # Step 1: Create or get a free test Subscription plan with tokens
        plan, created = Subscription.objects.update_or_create(
            package_name="Free Test Plan",
            defaults={
                "description": "Free test plan for project recommendation feature",
                "no_of_tokens": 100000,
                "no_of_profile_assessment": 10,
                "internship_access_type": "full",
                "job_portal_access_type": "full",
                "course_portal_access_type": "full",
                "project_topic_access_type": "full",
                "career_compare": True,
                "career_roadmap": True,
                "ai_chat_access": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} plan: {plan.package_name} "
                f"(ID: {plan.pk}, tokens: {plan.no_of_tokens})"
            )
        )

        # Step 2: Create or get a PlanPrice (free, $0)
        plan_price, price_created = PlanPrice.objects.update_or_create(
            plan=plan,
            period="monthly",
            defaults={
                "price": 0,
                "duration_days": 365,
                "is_active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if price_created else 'Updated'} PlanPrice: "
                f"Free Monthly (ID: {plan_price.pk})"
            )
        )

        # Step 3: Enable project_gen feature via SubscriptionFeature
        feature, feature_created = SubscriptionFeature.objects.update_or_create(
            subscription=plan,
            feature_code="project_gen",
            defaults={
                "feature_name": "Project Recommendations",
                "is_enabled": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if feature_created else 'Updated'} SubscriptionFeature: "
                f"project_gen (ID: {feature.pk})"
            )
        )

        # Step 4: Deactivate any existing active subscriptions for this user
        # to avoid collisions in check_token_available (which picks .first())
        start_date = now().date()
        active_subs = UserSubscription.objects.filter(
            user=user, is_active=True, deleted=False
        )
        deactivated_count = active_subs.update(
            is_active=False,
            end_date=start_date - timedelta(days=1),
        )
        if deactivated_count:
            self.stdout.write(
                f"Deactivated {deactivated_count} existing active subscription(s)"
            )

        # Step 5: Create fresh UserSubscription for the test user
        end_date = start_date + timedelta(days=365)

        user_sub, sub_created = UserSubscription.objects.get_or_create(
            user=user,
            plan_price=plan_price,
            is_active=True,
            defaults={
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if sub_created else 'Updated'} UserSubscription for "
                f"'{email}' (ID: {user_sub.pk}, valid: {start_date} → {end_date})"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ Setup complete! The user can now test:\n"
                f"   GET /api/project-recommendations/{{suggestion_id}}/\n"
                f"   Headers: Authorization: Bearer {{access_token}}"
            )
        )
