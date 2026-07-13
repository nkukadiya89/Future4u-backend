from django.db import migrations
from django.utils import timezone


STREAMS = [
    (
        "science",
        "Science",
        1,
        "Physics Chemistry Mathematics and Biology pathways for students continuing with science subjects",
        "higher_secondary",
    ),
    (
        "commerce",
        "Commerce",
        2,
        "Accounts Business Studies Economics and finance-oriented pathways",
        "higher_secondary",
    ),
    (
        "arts",
        "Arts & Humanities",
        3,
        "Humanities social sciences languages public affairs and liberal arts pathways",
        "higher_secondary",
    ),
    (
        "vocational",
        "Vocational / Skill-Based",
        4,
        "Practical job-oriented learning through vocational or skill-based programs",
        "higher_secondary",
    ),
    (
        "sports",
        "Sports & Physical Education",
        5,
        "Sports training physical education fitness and performance-focused pathways",
        "higher_secondary",
    ),
    (
        "fine_arts",
        "Fine Arts & Creative Studies",
        6,
        "Visual arts performing arts design and creative practice pathways",
        "higher_secondary",
    ),
    (
        "agriculture",
        "Agriculture",
        7,
        "Agriculture horticulture food systems and rural development pathways",
        "higher_secondary",
    ),
    (
        "higher_secondary_other",
        "Other / Not Listed",
        8,
        "Use this when the student's current higher-secondary stream is not listed",
        "higher_secondary",
    ),
    (
        "iti_electrician",
        "Electrician / Wireman",
        101,
        "Electrical wiring installation repair and maintenance trades",
        "iti",
    ),
    (
        "iti_fitter",
        "Fitter / Machinist",
        102,
        "Fitting machining tools fabrication and workshop practice trades",
        "iti",
    ),
    (
        "iti_welder",
        "Welder / Fabricator",
        103,
        "Welding fabrication metalwork and industrial production trades",
        "iti",
    ),
    (
        "iti_electronics",
        "Electronics Technician",
        104,
        "Electronic circuits devices installation testing and repair trades",
        "iti",
    ),
    (
        "iti_computer_it",
        "Computer Hardware & IT Support",
        105,
        "Computer hardware networking software support and IT service trades",
        "iti",
    ),
    (
        "iti_automobile",
        "Automobile Technician",
        106,
        "Vehicle servicing repair diagnostics and automobile systems trades",
        "iti",
    ),
    (
        "iti_carpenter",
        "Carpenter",
        107,
        "Woodwork furniture making interiors and construction support trades",
        "iti",
    ),
    (
        "iti_plumber",
        "Plumber",
        108,
        "Piping plumbing sanitation installation and maintenance trades",
        "iti",
    ),
    (
        "iti_beauty_wellness",
        "Beauty & Wellness",
        109,
        "Beauty grooming salon wellness and personal care service trades",
        "iti",
    ),
    (
        "iti_healthcare",
        "Healthcare Assistant",
        110,
        "Patient support basic clinical assistance and healthcare service trades",
        "iti",
    ),
    (
        "iti_other",
        "Other ITI Trade",
        111,
        "Use this when the student's ITI or vocational trade is not listed",
        "iti",
    ),
    (
        "diploma_engineering",
        "Engineering Diploma",
        201,
        "Civil mechanical electrical electronics automobile and related engineering diplomas",
        "diploma",
    ),
    (
        "diploma_computer_it",
        "Computer Science & IT Diploma",
        202,
        "Computer engineering software networking programming and IT diplomas",
        "diploma",
    ),
    (
        "diploma_medical",
        "Medical Lab & Paramedical Diploma",
        203,
        "Medical lab pharmacy nursing assistant and allied healthcare diplomas",
        "diploma",
    ),
    (
        "diploma_business",
        "Business & Management Diploma",
        204,
        "Business management office administration finance and commerce diplomas",
        "diploma",
    ),
    (
        "diploma_hotel_management",
        "Hospitality & Tourism Diploma",
        205,
        "Hotel management travel tourism culinary and hospitality diplomas",
        "diploma",
    ),
    (
        "diploma_design",
        "Design & Creative Diploma",
        206,
        "Fashion design animation interior design and creative arts diplomas",
        "diploma",
    ),
    (
        "diploma_agriculture",
        "Agriculture Diploma",
        207,
        "Agriculture horticulture dairy technology and related diplomas",
        "diploma",
    ),
    (
        "diploma_other",
        "Other Diploma",
        208,
        "Use this when the student's diploma specialization is not listed",
        "diploma",
    ),
]

RENAMED_CODES = {
    "diploma_engineering_technical": "diploma_engineering",
    "diploma_health_paramedical": "diploma_medical",
    "diploma_business_commerce": "diploma_business",
    "diploma_hospitality_tourism": "diploma_hotel_management",
    "diploma_design_creative": "diploma_design",
}


def refresh_stream_catalog(apps, schema_editor):
    EducationLevel = apps.get_model("education_level", "EducationLevel")
    Stream = apps.get_model("stream", "Stream")

    # Fresh installs are populated by init_data after migrations. This
    # migration only reshapes catalogs that already exist on deployed systems.
    if not Stream.objects.exists():
        return

    levels = {level.level_code.lower(): level for level in EducationLevel.objects.all()}

    # Free the globally unique sequence_order values before reordering.
    for offset, stream in enumerate(Stream.objects.order_by("pk"), start=1):
        Stream.objects.filter(pk=stream.pk).update(sequence_order=10000 + offset)

    for old_code, new_code in RENAMED_CODES.items():
        old_stream = Stream.objects.filter(stream_code__iexact=old_code).first()
        new_stream = Stream.objects.filter(stream_code__iexact=new_code).first()
        if old_stream and not new_stream:
            Stream.objects.filter(pk=old_stream.pk).update(stream_code=new_code)

    active_codes = []
    timestamp = timezone.now()
    for code, name, sequence, description, level_code in STREAMS:
        level = levels.get(level_code)
        stream = Stream.objects.filter(stream_code__iexact=code).first()
        if stream is None:
            stream = Stream(stream_code=code)
        stream.stream_name = name
        stream.sequence_order = sequence
        stream.description = description
        stream.education_level = level
        stream.is_active = True
        stream.deleted = False
        stream.deleted_at = None
        stream.deleted_by = None
        stream.updated_at = timestamp
        stream.save()
        active_codes.append(code)

    legacy_streams = Stream.objects.exclude(stream_code__in=active_codes)
    for offset, stream in enumerate(legacy_streams.order_by("pk"), start=1):
        stream.sequence_order = 20000 + offset
        stream.is_active = False
        stream.deleted = True
        stream.deleted_at = timestamp
        stream.save(
            update_fields=[
                "sequence_order",
                "is_active",
                "deleted",
                "deleted_at",
                "updated_at",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("stream", "0005_alter_stream_updated_at"),
    ]

    operations = [
        migrations.RunPython(
            refresh_stream_catalog,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
