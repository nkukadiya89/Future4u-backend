from django.db import migrations, models
from django.db.models import Q

SPORTS_KEYWORDS = (
    "physical activity",
    "physically active",
    "competitive",
    "coaching",
)


def _sports_domains(Domain):
    domains = list(Domain.objects.filter(domain_code__iexact="sports", deleted=False))
    if domains:
        return domains
    return list(Domain.objects.filter(domain_name__icontains="sport", deleted=False))


def tag_sports_questions(apps, schema_editor):
    Question = apps.get_model("assessment", "Question")
    Domain = apps.get_model("domain", "Domain")

    sports_domains = _sports_domains(Domain)
    if not sports_domains:
        return

    selected_ids = []
    for keyword in SPORTS_KEYWORDS:
        q = (
            Question.objects.filter(question_text__icontains=keyword)
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )
        if q and q not in selected_ids:
            selected_ids.append(q)
        if len(selected_ids) >= 4:
            break

    if len(selected_ids) < 2:
        fallback_ids = list(
            Question.objects.filter(
                Q(question_text__icontains="activity")
                | Q(question_text__icontains="active")
                | Q(question_text__icontains="sport")
                | Q(question_text__icontains="competitive")
                | Q(question_text__icontains="coach")
                | Q(question_text__icontains="team")
            )
            .order_by("id")
            .values_list("id", flat=True)[:4]
        )
        for qid in fallback_ids:
            if qid not in selected_ids:
                selected_ids.append(qid)
            if len(selected_ids) >= 4:
                break

    if not selected_ids:
        return

    through_model = Question.mapped_domains.through
    for question_id in selected_ids:
        Question.objects.filter(id=question_id).update(signal_strength=2)
        for domain in sports_domains:
            through_model.objects.get_or_create(
                question_id=question_id,
                domain_id=domain.id,
            )


def untag_sports_questions(apps, schema_editor):
    Question = apps.get_model("assessment", "Question")
    Domain = apps.get_model("domain", "Domain")
    through_model = Question.mapped_domains.through

    sports_domains = _sports_domains(Domain)
    if not sports_domains:
        return

    sports_domain_ids = [d.id for d in sports_domains]
    questions = Question.objects.filter(
        Q(question_text__icontains="activity")
        | Q(question_text__icontains="active")
        | Q(question_text__icontains="sport")
        | Q(question_text__icontains="competitive")
        | Q(question_text__icontains="coach")
        | Q(question_text__icontains="team")
    )
    through_model.objects.filter(
        question_id__in=questions.values_list("id", flat=True),
        domain_id__in=sports_domain_ids,
    ).delete()
    questions.update(signal_strength=1)


class Migration(migrations.Migration):
    dependencies = [
        ("domain", "0002_initial"),
        ("assessment", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="mapped_domains",
            field=models.ManyToManyField(
                blank=True,
                related_name="assessment_questions",
                to="domain.domain",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="signal_strength",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.RunPython(tag_sports_questions, untag_sports_questions),
    ]
