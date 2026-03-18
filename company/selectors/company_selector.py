from company.models import Company


def get_active_company_queryset():
    return (
        Company.objects.filter(deleted=0)
        .select_related(
            "created_by",
            "updated_by",
            "registered_business_address_pincode",
            "trading_address_pincode",
        )
        .prefetch_related("key_person", "attachment", "company_email", "company_percentage")
        .order_by("-id")
    )
