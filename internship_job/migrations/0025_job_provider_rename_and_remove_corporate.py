from django.db import migrations


def backfill_job_provider_from_corporate(apps, schema_editor):
    Job = apps.get_model("internship_job", "Job")
    jobs = list(
        Job.objects.filter(
            job_provider__isnull=True,
            corporate__isnull=False,
            corporate__user__isnull=False,
        ).select_related("corporate")
    )

    for job in jobs:
        job.job_provider_id = job.corporate.user_id

    if jobs:
        Job.objects.bulk_update(jobs, ["job_provider"])
        print(
            f"  Fixed {len(jobs)} job(s) with null job_provider backfilled from corporate.user"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("internship_job", "0024_fix_null_internship_provider"),
        ("user_profile", "0047_remove_legacy_corporate_add_org_profiles"),
    ]

    operations = [
        migrations.RenameField(
            model_name="job",
            old_name="provider",
            new_name="job_provider",
        ),
        migrations.RunPython(
            backfill_job_provider_from_corporate, migrations.RunPython.noop
        ),
    ]
