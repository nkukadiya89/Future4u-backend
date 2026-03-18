from django.db import transaction

from company.models import Company, CompanyProfile
from user.models import User


class CompanyRepository:
    @transaction.atomic
    def create_company_with_admin(
        self,
        company_data: dict,
        user_data: dict,
        password: str,
        actor=None,
    ):
        user = User.objects.create(**user_data)
        user.set_password(password)
        user.save()

        company = Company.objects.create(**company_data)
        user.company = company
        user.save(update_fields=["company"])

        CompanyProfile.objects.get_or_create(company=company)

        if actor is not None and company.created_by is None:
            company.created_by = actor
            company.updated_by = actor
            company.save(update_fields=["created_by", "updated_by"])

        return company, user

    @transaction.atomic
    def update_company(self, company: Company, update_data: dict, actor=None):
        changed_fields = []
        for field, value in update_data.items():
            if hasattr(company, field):
                setattr(company, field, value)
                changed_fields.append(field)

        if actor is not None and hasattr(company, "updated_by"):
            company.updated_by = actor
            changed_fields.append("updated_by")

        if changed_fields:
            company.save(update_fields=list(set(changed_fields)))
        else:
            company.save()

        # Keep linked users in sync for key profile fields.
        user_changed_fields = []
        for field in ("first_name", "designation", "email", "phone"):
            if field in update_data:
                user_changed_fields.append(field)

        if user_changed_fields:
            for user in User.objects.filter(company=company):
                for field in user_changed_fields:
                    setattr(user, field, getattr(company, field))
                user.save(update_fields=user_changed_fields)

        return company
