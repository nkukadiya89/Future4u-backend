import logging
import re

from django.contrib.auth import get_user_model
from django.utils.html import strip_tags

from company.models import Company

User = get_user_model()
logger = logging.getLogger(__name__)


def clean_html_content(html_content):
    if not html_content:
        return ""

    # Remove CSS styles within <style> tags
    html_content = re.sub(
        r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove scripts
    html_content = re.sub(
        r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove HTML comments
    html_content = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)

    # Remove common structural elements that don't contain meaningful data
    html_content = re.sub(
        r"<head[^>]*>.*?</head>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )
    html_content = re.sub(r"<meta[^>]*>", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"<link[^>]*>", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"<!DOCTYPE[^>]*>", "", html_content, flags=re.IGNORECASE)

    # Remove common non-meaningful elements
    html_content = re.sub(
        r'<(div|span)[^>]*class="[^"]*(header|footer|nav|sidebar|menu)[^"]*"[^>]*>.*?</\1>',
        "",
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Strip remaining HTML tags
    clean_text = strip_tags(html_content)

    # Clean up extra whitespace and newlines
    clean_text = re.sub(r"\s+", " ", clean_text)
    clean_text = clean_text.strip()

    # Remove common email template boilerplate text
    boilerplate_patterns = [
        r"This is an automated message.*?please do not reply\.?",
        r"Best regards,.*?Team.*",
        r"Sent from.*?",
        r"\.\.\..*?\.\.\.",
        r"---.*?---",
    ]

    for pattern in boilerplate_patterns:
        clean_text = re.sub(pattern, "", clean_text, flags=re.IGNORECASE)

    # Final cleanup
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    return clean_text


def find_related_objects_from_email(email_address):

    result = {
        "user": None,
        "user_id": None,
        "company": None,
        "company_id": None,
        "partner_company": None,
        "partner_company_id": None,
        "end_client": None,
        "end_client_id": None,
    }

    # Find user by email
    user = User.objects.filter(email=email_address).first()
    result["user"] = user
    result["user_id"] = str(user.id) if user else None

    # Find company by email
    company = Company.objects.filter(email=email_address).first()
    result["company"] = company
    result["company_id"] = str(company.id) if company else None

    # partner_company / end_client removed from the project.
    # Keep the keys for backwards compatibility with callers.
    result["partner_company"] = None
    result["partner_company_id"] = None
    result["end_client"] = None
    result["end_client_id"] = None

    return result


def extract_recipients_from_email_field(email_field):

    if not email_field:
        return []

    # Split by comma and clean up
    emails = []
    for email in email_field.split(","):
        email = email.strip()
        if email:
            emails.append(email)

    return emails


def find_related_objects_from_email(email_address):

    result = {
        "user": None,
        "user_id": None,
        "company": None,
        "company_id": None,
        "partner_company": None,
        "partner_company_id": None,
        "end_client": None,
        "end_client_id": None,
    }

    # Find user by email
    user = User.objects.filter(email=email_address).first()
    result["user"] = user
    result["user_id"] = str(user.id) if user else None

    # Find company by email
    company = Company.objects.filter(email=email_address).first()
    result["company"] = company
    result["company_id"] = str(company.id) if company else None

    # partner_company / end_client removed from the project.
    # Keep the keys for backwards compatibility with callers.
    result["partner_company"] = None
    result["partner_company_id"] = None
    result["end_client"] = None
    result["end_client_id"] = None

    return result


def extract_recipients_from_email_field(email_field):

    if not email_field:
        return []

    # Split by comma and clean up
    emails = []
    for email in email_field.split(","):
        email = email.strip()
        if email:
            emails.append(email)

    return emails


# def log_email_notification(
#     recipient_email,
#     subject,
#     message_content,
#     sender_email,
#     email_type=None,
#     status="sent",
#     error_message=None,
#     recipient_id=None,
#     sender_id=None,
#     related_partner_company=None,
#     related_company=None,
#     related_end_client=None,
# ):

#     try:
#         # Clean HTML content and store only plain text
#         clean_message = clean_html_content(message_content)

#         # Truncate if too long for storage
#         if len(clean_message) > 50000:
#             clean_message = clean_message[:50000] + "...[truncated]"

#         # Auto-populate recipient_id and sender_id if not provided
#         if not recipient_id:
#             recipient_objects = find_related_objects_from_email(recipient_email)
#             # Prioritize user_id, then company_id, then partner_company_id, then end_client_id
#             recipient_id = (
#                 recipient_objects["user_id"]
#                 or recipient_objects["company_id"]
#                 or recipient_objects["partner_company_id"]
#                 or recipient_objects["end_client_id"]
#             )

#         if not sender_id:
#             sender_objects = find_related_objects_from_email(sender_email)
#             # Prioritize user_id, then company_id, then partner_company_id, then end_client_id
#             sender_id = (
#                 sender_objects["user_id"]
#                 or sender_objects["company_id"]
#                 or sender_objects["partner_company_id"]
#                 or sender_objects["end_client_id"]
#             )EmailLog

#         .objects.create(
#             recipient_email=recipient_email,
#             recipient_id=recipient_id,
#             subject=subject,
#             message_content=clean_message,
#             sender_email=sender_email,
#             sender_id=sender_id,
#             email_type=email_type,
#             status=status,
#             error_message=error_message,
#             related_partner_company=related_partner_company,
#             related_company=related_company,
#             related_end_client=related_end_client,
#         )

#         logger.info(f"Email logged: {subject} to {recipient_email} - Status: {status}")

#     except Exception as e:
#         logger.error(f"Failed to log email: {str(e)}")


def log_email_sent(
    email_obj,
    email_type=None,
    recipient_id=None,
    sender_id=None,
    related_partner_company=None,
    related_company=None,
    related_end_client=None,
    custom_message_content=None,
):

    try:
        # Handle different email object types
        if hasattr(email_obj, "to"):  # EmailMultiAlternatives
            recipients = email_obj.to
            subject = getattr(email_obj, "subject", "No Subject")
            from_email = getattr(
                email_obj,
                "from_email",
                email_obj.from_email if hasattr(email_obj, "from_email") else "Unknown",
            )
            # EmailMultiAlternatives has alternatives - try to get HTML content first
            body = getattr(email_obj, "body", "No Body")
            # Check if there are HTML alternatives
            if hasattr(email_obj, "alternatives") and email_obj.alternatives:
                for content, content_type in email_obj.alternatives:
                    if content_type == "text/html":
                        body = content
                        break
        else:  # MIMEMultipart
            # Extract recipients from To field
            to_field = email_obj["To"] if email_obj["To"] else ""
            recipients = extract_recipients_from_email_field(to_field)
            subject = email_obj["Subject"] if email_obj["Subject"] else "No Subject"
            from_email = email_obj["From"] if email_obj["From"] else "Unknown"
            # For MIMEMultipart, extract HTML content first, then fallback to text
            body = "No Body"
            html_content = None
            text_content = None

            for part in email_obj.walk():
                if part.get_content_type() == "text/html":
                    html_content = part.get_payload(decode=True).decode(
                        "utf-8", errors="ignore"
                    )
                elif part.get_content_type() == "text/plain":
                    text_content = part.get_payload(decode=True).decode(
                        "utf-8", errors="ignore"
                    )

            # Use HTML content if available, otherwise use text content
            body = html_content if html_content else (text_content or "No Body")

        if recipients:
            for recipient in recipients:
                # If related objects are not provided, try to find them from email
                if not any(
                    [related_company, related_partner_company, related_end_client]
                ):
                    found_objects = find_related_objects_from_email(recipient)

                    # Use found objects if not explicitly provided
                    final_company = related_company or found_objects["company"]
                    final_partner_company = (
                        related_partner_company or found_objects["partner_company"]
                    )
                    final_end_client = related_end_client or found_objects["end_client"]

                    # Auto-populate recipient_id if not provided
                    final_recipient_id = recipient_id
                    if not final_recipient_id:
                        final_recipient_id = (
                            found_objects["user_id"]
                            or found_objects["company_id"]
                            or found_objects["partner_company_id"]
                            or found_objects["end_client_id"]
                        )
                else:
                    final_company = related_company
                    final_partner_company = related_partner_company
                    final_end_client = related_end_client
                    final_recipient_id = recipient_id

                # Auto-populate sender_id if not provided
                final_sender_id = sender_id
                if not final_sender_id:
                    sender_objects = find_related_objects_from_email(from_email)
                    final_sender_id = (
                        sender_objects["user_id"]
                        or sender_objects["company_id"]
                        or sender_objects["partner_company_id"]
                        or sender_objects["end_client_id"]
                    )

    except Exception as e:
        logger.error(f"Failed to log sent email: {str(e)}")


def log_email_failed(
    recipient_email,
    subject,
    error_message,
    sender_email,
    email_type=None,
    recipient_id=None,
    sender_id=None,
    related_partner_company=None,
    related_company=None,
    related_end_client=None,
):

    # If related objects are not provided, try to find them from email
    if not any([related_company, related_partner_company, related_end_client]):
        found_objects = find_related_objects_from_email(recipient_email)

        # Use found objects if not explicitly provided
        final_company = related_company or found_objects["company"]
        final_partner_company = (
            related_partner_company or found_objects["partner_company"]
        )
        final_end_client = related_end_client or found_objects["end_client"]

        # Auto-populate recipient_id if not provided
        final_recipient_id = recipient_id
        if not final_recipient_id:
            final_recipient_id = (
                found_objects["user_id"]
                or found_objects["company_id"]
                or found_objects["partner_company_id"]
                or found_objects["end_client_id"]
            )
    else:
        final_company = related_company
        final_partner_company = related_partner_company
        final_end_client = related_end_client
        final_recipient_id = recipient_id

    # Auto-populate sender_id if not provided
    final_sender_id = sender_id
    if not final_sender_id:
        sender_objects = find_related_objects_from_email(sender_email)
        final_sender_id = (
            sender_objects["user_id"]
            or sender_objects["company_id"]
            or sender_objects["partner_company_id"]
            or sender_objects["end_client_id"]
        )
