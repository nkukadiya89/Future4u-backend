"""
Data migration: calibrate parent_acceptance_level per domain.

Scale: 1 = low (risky in Indian parent eyes)
       2 = moderate (acceptable with explanation)
       3 = high (traditional respected fields)

Based on Indian parent mindset, especially Gujarat context.
"""

from django.db import migrations


# domain_code -> parent_acceptance_level
# Scale: 1=Low (risky), 2=Moderate (acceptable), 3=High (respected), 4=Very High, 5=Extremely High
PARENT_ACCEPTANCE = {
    # EXTREMELY HIGH (5) — Doctor, IAS, Armed Forces, CA, Banking
    "mbbs_medicine": 5,
    "nursing": 5,
    "pharmacy": 5,
    "dentistry": 5,
    "upsc_civil_services": 5,
    "state_govt_services": 5,
    "banking_govt": 5,
    "defense_armed_forces": 5,
    "ca_accounting": 5,
    "banking_finance": 5,
    "teaching_school": 5,
    # VERY HIGH (4) — Engineering, Law, Veterinary, Physiotherapy
    "civil_engineering": 4,
    "mechanical_engineering": 4,
    "electrical_engineering": 4,
    "chemical_engineering": 4,
    "manufacturing": 4,
    "law_practice": 4,
    "higher_education": 4,
    "biotech": 4,
    "pharma": 4,
    "space_tech": 4,
    "veterinary": 4,
    "physiotherapy": 4,
    "ayurveda_homeopathy": 4,
    "healthtech": 4,
    "med_devices": 4,
    "fintech": 4,
    "police_law_enforcement": 4,
    # HIGH (3) — Tech-adjacent, agriculture, hospitality, niche engineering
    "nanotech": 3,
    "quantum": 3,
    "insurance_tech": 3,
    "supply_chain": 3,
    "legaltech": 3,
    "defense_tech": 3,
    "robotics": 3,
    "ev_mobility": 3,
    "renewable_energy": 3,
    "construction_tech": 3,
    "agriculture_farming": 3,
    "horticulture": 3,
    "foodtech": 3,
    "pure_sciences": 3,
    "architecture": 3,
    "hotel_management": 3,
    "hrtech": 3,
    "electrician_trades": 3,
    "plumbing_civil_trades": 3,
    "it_hardware_support": 3,
    "urban_tech": 3,
    "physical_education": 3,
    "business_management": 3,
    "entrepreneurship": 3,
    # MODERATE (2) — Tech fields, digital, social work
    "ai_data": 2,
    "data_engineering": 2,
    "cloud_computing": 2,
    "cybersecurity": 2,
    "devops": 2,
    "iot": 2,
    "blockchain": 2,
    "ai_ethics": 2,
    "edtech": 2,
    "ecommerce": 2,
    "agritech": 2,
    "climate_tech": 2,
    "traveltech": 2,
    "marketing": 2,
    "journalism_media": 2,
    "sports_coaching": 2,
    "sports_tech": 2,
    "social_work": 2,
    "psychology_counselling": 2,
    "beauty_wellness": 2,
    # LOW (1) — Non-traditional, seen as risky by Indian parents
    "gaming": 1,
    "creator_economy": 1,
    "fashiontech": 1,
    "fashion_design": 1,
    "fine_arts_design": 1,
    "performing_arts": 1,
    "mental_health": 1,
    "ar_vr": 1,
    "digital_marketing": 1,
    "professional_sports": 1,
}


def calibrate(apps, schema_editor):
    Domain = apps.get_model("domain", "Domain")
    for code, level in PARENT_ACCEPTANCE.items():
        Domain.objects.filter(domain_code=code).update(parent_acceptance_level=level)


def reverse_calibrate(apps, schema_editor):
    Domain = apps.get_model("domain", "Domain")
    Domain.objects.filter(domain_code__in=PARENT_ACCEPTANCE.keys()).update(
        parent_acceptance_level=3
    )


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0011_domainreportmeta_direction_why"),
    ]

    operations = [
        migrations.RunPython(calibrate, reverse_calibrate),
    ]
