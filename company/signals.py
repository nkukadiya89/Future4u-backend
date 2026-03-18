from django.db.models.signals import post_save
from django.dispatch import receiver

from company.models import Company, CompanyProfile
from user.models import CustomGroup


@receiver(post_save, sender=Company)
def create_company_profile(sender, instance, created, **kwargs):
    if created:
        CompanyProfile.objects.create(company=instance)


@receiver(post_save, sender=Company)
def update_company_perc(sender, instance, created, **kwargs):
    if created:
        company = Company.objects.get(id=instance.id)
        if (
            company.name
            and company.gst_no
            and company.name
            and company.cin_no
            and company.first_name
            and company.designation
            and company.email
            and company.phone
            and company.registered_business_address_building
            and company.registered_business_address_area
            and company.registered_business_address_landmark
            and company.registered_business_address_state
            and company.registered_business_address_city
            and company.registered_business_address_pincode
            and company.trading_address_building
            and company.trading_address_area
            and company.trading_address_landmark
            and company.trading_address_state
            and company.trading_address_city
            and company.trading_address_pincode
        ) is not None:
            company_profile = CompanyProfile.objects.get(company=instance)
            company_profile.company_perc = 30
            company_profile.save()


@receiver(post_save, sender=CustomGroup)
def create_user_group(sender, instance, created, **kwargs):
    if instance.company:
        if created:
            user_group_count = CustomGroup.objects.filter(
                company=instance.company, deleted=0
            ).count()
            if user_group_count >= 1:
                company_profile = CompanyProfile.objects.get(company=instance.company)
                company_profile.user_role_perc = 10
                company_profile.save()
