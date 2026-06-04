import csv
from io import StringIO

from django.db import migrations
from django.utils import timezone


# Snapshot of stream_master_sample.csv for populated databases.
STREAM_CATALOG = """stream_code,stream_name,sequence_order,description,education_level
science_pcm,Science (PCM),1,Physics Chemistry Mathematics,higher_secondary
science_pcb,Science (PCB),2,Physics Chemistry Biology,higher_secondary
commerce,Commerce,3,Accountancy Business Studies Economics,higher_secondary
arts,Arts & Humanities,4,History Political Science Psychology Sociology,higher_secondary
vocational,Vocational / Skill-Based,5,Practical job-oriented skill-based programs,higher_secondary
higher_secondary_other,Other / Not Listed,6,Stream not listed above,higher_secondary
iti_electrician,Electrician / Wireman,101,Electrical wiring installation repair and maintenance,iti
iti_fitter,Fitter / Machinist,102,Fitting machining and workshop practice,iti
iti_welder,Welder / Fabricator,103,Welding fabrication and metalwork,iti
iti_electronics,Electronics Technician,104,Electronic circuits devices and repair,iti
iti_computer_it,Computer Hardware & IT Support,105,Computer hardware networking and IT support,iti
iti_automobile,Automobile Technician,106,Vehicle servicing repair and diagnostics,iti
iti_carpenter,Carpenter,107,Woodwork furniture making and interiors,iti
iti_plumber,Plumber,108,Piping plumbing sanitation installation and maintenance,iti
iti_beauty_wellness,Beauty & Wellness,109,Beauty grooming salon and personal care,iti
iti_healthcare,Healthcare Assistant,110,Patient support and basic clinical assistance,iti
iti_other,Other ITI Trade,111,Trade not listed above,iti
diploma_engineering,Engineering Diploma,201,Civil mechanical electrical electronics and automobile,diploma
diploma_computer_it,Computer Science & IT Diploma,202,Computer engineering software and networking,diploma
diploma_medical,Medical Lab & Paramedical Diploma,203,Medical lab pharmacy nursing and allied healthcare,diploma
diploma_business,Business & Management Diploma,204,Business management office administration and finance,diploma
diploma_hotel_management,Hospitality & Tourism Diploma,205,Hotel management travel tourism and culinary,diploma
diploma_design,Design & Creative Diploma,206,Fashion design animation interior and creative arts,diploma
diploma_agriculture,Agriculture Diploma,207,Agriculture horticulture and dairy technology,diploma
diploma_other,Other Diploma,208,Diploma specialization not listed above,diploma
grad_science_pcm,Science PCM (B.Sc.),301,Physics Chemistry Mathematics Statistics,graduation
grad_science_pcb,Science PCB (B.Sc.),302,Biology Chemistry Biotechnology Microbiology,graduation
grad_commerce,Commerce (B.Com),303,Accounting Finance Banking Taxation Business Studies,graduation
grad_arts,Arts & Humanities (B.A.),304,History Political Science Psychology Sociology Economics English Literature Geography,graduation
grad_engineering,Engineering & Technology (B.Tech/BE),305,Computer Science Mechanical Civil Electrical Electronics Chemical Aerospace,graduation
grad_medical,Medical & Health Sciences,306,MBBS BDS BAMS BHMS B.Pharm B.Sc Nursing BPT,graduation
grad_management,Business Administration (BBA/BMS),307,Marketing Finance Human Resources Operations Entrepreneurship,graduation
grad_computer_app,Computer Applications (BCA),308,Software Development Web Technologies Database Management Programming,graduation
grad_law,Law (LL.B / Integrated),309,LL.B BA-LLB BBA-LLB Constitutional Corporate and Criminal Law,graduation
grad_agriculture,Agriculture & Allied,310,Agriculture Horticulture Forestry Fisheries Dairy Technology Food Science,graduation
grad_design,Design & Creative Arts (B.Des),311,Fashion Design Graphic Design Interior Design Animation Industrial Design,graduation
grad_hotel_management,Hotel Management & Tourism (BHM),312,Hospitality Hotel Administration Travel Tourism Culinary Arts,graduation
grad_media,Media & Mass Communication,313,Journalism Broadcast Media Digital Media Advertising Public Relations,graduation
grad_education,Education (B.Ed),314,Teaching Pedagogy Educational Psychology Curriculum Design,graduation
grad_other,Other / Not Listed,315,Graduation major not listed above,graduation
pg_science,Science (M.Sc.),401,Physics Chemistry Mathematics Biology Data Science Environmental Science Biotechnology,post_graduation
pg_commerce,Commerce (M.Com),402,Accounting Finance Taxation International Business Banking,post_graduation
pg_arts,Arts & Humanities (M.A.),403,History Psychology Sociology Economics Literature Political Science Linguistics,post_graduation
pg_engineering,Engineering & Technology (M.Tech/ME),404,Computer Science VLSI Structural Thermal Power Systems AI-ML,post_graduation
pg_management,Management (MBA/PGDM),405,Marketing Finance Human Resources Operations Business Analytics Strategy,post_graduation
pg_computer_app,Computer Applications (MCA),406,Software Engineering Cloud Computing AI-ML Data Analytics Cybersecurity,post_graduation
pg_medical,Medical Specialization (MD/MS),407,General Medicine Surgery Pediatrics Gynecology Orthopedics Radiology Psychiatry,post_graduation
pg_pharmacy,Pharmacy (M.Pharm),408,Pharmaceutics Pharmacology Pharmacognosy Pharmaceutical Chemistry,post_graduation
pg_nursing,Nursing & Paramedical,409,M.Sc. Nursing MPT MPH Medical Lab Technology Optometry,post_graduation
pg_law,Law (LL.M),410,Constitutional Law Corporate Law International Law Human Rights Criminal Law,post_graduation
pg_education,Education (M.Ed),411,Educational Leadership Curriculum Development Special Education EdTech,post_graduation
pg_other,Other / Not Listed,412,Postgraduate specialization not listed above,post_graduation
phd_sciences,STEM Sciences,501,Physics Chemistry Biology Mathematics Computer Science Engineering,doctorate
phd_medical,Medical & Health Sciences,502,Medicine Public Health Pharmacy Nursing Biotechnology Epidemiology,doctorate
phd_arts_humanities,Arts & Humanities,503,History Literature Philosophy Languages Cultural Studies Linguistics,doctorate
phd_social_sciences,Social Sciences,504,Economics Sociology Political Science Psychology Geography Anthropology,doctorate
phd_management,Management & Commerce,505,Finance Marketing Organizational Behavior Strategy Economics,doctorate
phd_law,Law & Legal Studies,506,Constitutional Law Jurisprudence International Law Legal Philosophy,doctorate
phd_education,Education,507,Educational Policy Pedagogy Curriculum Studies Educational Psychology,doctorate
phd_agriculture,Agriculture & Allied,508,Agronomy Plant Science Soil Science Food Technology Veterinary Science,doctorate
phd_interdisciplinary,Interdisciplinary,509,Cross-disciplinary research across multiple fields,doctorate
phd_other,Other / Not Listed,510,Doctoral research field not listed above,doctorate
prof_finance,Finance & Accounting,601,CA CFA ACCA CMA CFP CPA,professional
prof_corporate_law,Company Secretary (CS),602,Corporate Governance Compliance Secretarial Practice,professional
prof_tech,Technology Certifications,603,AWS Azure GCP PMP PRINCE2 Scrum Master DevOps ITIL,professional
prof_data_science,Data Science & AI,604,Machine Learning Data Engineering Business Intelligence Deep Learning NLP,professional
prof_cybersecurity,Cybersecurity,605,CEH CISSP CISM CompTIA Security+ CISA,professional
prof_digital_marketing,Digital Marketing,606,Google Analytics HubSpot SEO SEM Social Media Marketing Content Strategy,professional
prof_healthcare,Healthcare Certifications,607,Medical Coding CPC Clinical Research Pharmacovigilance Health Administration,professional
prof_supply_chain,Supply Chain & Logistics,608,CSCP CPSM CLTD Six Sigma Green Belt Lean Management,professional
prof_hr,Human Resources,609,SHRM-CP SHRM-SCP CIPD Talent Management HR Analytics,professional
prof_other,Other / Not Listed,610,Certification not listed above,professional
"""

RENAMED_CODES = {
    "science": "science_pcm",
}


def stream_rows():
    return csv.DictReader(StringIO(STREAM_CATALOG))


def sync_latest_stream_catalog(apps, schema_editor):
    EducationLevel = apps.get_model("education_level", "EducationLevel")
    Stream = apps.get_model("stream", "Stream")

    # Fresh installs are populated by init_data after migrations.
    if not Stream.objects.exists():
        return

    levels = {
        level.level_code.lower(): level
        for level in EducationLevel.objects.all()
    }

    # Free globally unique sequence values before assigning the new catalog.
    for offset, stream in enumerate(Stream.objects.order_by("pk"), start=1):
        Stream.objects.filter(pk=stream.pk).update(sequence_order=30000 + offset)

    for old_code, new_code in RENAMED_CODES.items():
        old_stream = Stream.objects.filter(stream_code__iexact=old_code).first()
        new_stream = Stream.objects.filter(stream_code__iexact=new_code).first()
        if old_stream and not new_stream:
            Stream.objects.filter(pk=old_stream.pk).update(stream_code=new_code)

    active_codes = []
    timestamp = timezone.now()
    for row in stream_rows():
        code = row["stream_code"]
        stream = Stream.objects.filter(stream_code__iexact=code).first()
        if stream is None:
            stream = Stream(stream_code=code)
        stream.stream_name = row["stream_name"]
        stream.sequence_order = int(row["sequence_order"])
        stream.description = row["description"]
        stream.education_level = levels.get(row["education_level"])
        stream.is_active = True
        stream.deleted = False
        stream.deleted_at = None
        stream.deleted_by = None
        stream.updated_at = timestamp
        stream.save()
        active_codes.append(code)

    legacy_streams = Stream.objects.exclude(stream_code__in=active_codes)
    for offset, stream in enumerate(legacy_streams.order_by("pk"), start=1):
        stream.sequence_order = 40000 + offset
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
        ("stream", "0006_refresh_stream_catalog"),
    ]

    operations = [
        migrations.RunPython(
            sync_latest_stream_catalog,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
