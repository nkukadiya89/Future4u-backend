import logging
import os

from celery import shared_task
from django.contrib.auth import get_user_model
from user.services.bulk_user_upload import BulkUserUploadService
from email_utils.send_email import send_admin_summary_email, send_mail

User = get_user_model()
logger = logging.getLogger(__name__)


def _serialize_bulk_upload_result(result):
    return {
        "total_records": int(result["total_records"]),
        "inserted": int(result["inserted"]),
        "failed": int(result["failed"]),
        "skipped": int(result["skipped"]),
        "errors": [
            {
                "row": int(err["row"]),
                "email": err.get("email"),
                "message": str(err["message"]),
            }
            for err in result.get("errors", [])
        ],
    }


@shared_task
def send_temp_password_email_task(name, email, temporary_password):
    send_mail(
        "Your Future4U Temporary Password",
        "temporary-password.html",
        {
            "name": name,
            "email": email,
            "temporary_password": temporary_password,
        },
    )


@shared_task
def bulk_upload_user_task(file_path, admin_id):
    try:
        admin_user = User.objects.get(id=admin_id)
        result = BulkUserUploadService.process_file_path(
            file_path,
            admin_user,
        )
        serialized = _serialize_bulk_upload_result(result)

        logger.info("Sending bulk upload summary to %s", admin_user.email)
        send_admin_summary_email(admin_user, serialized)
        logger.info("Bulk upload summary sent to %s", admin_user.email)

        return serialized
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
