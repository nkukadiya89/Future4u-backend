# import threading
# from django.conf import settings
# from decouple import config
# from django.template.loader import render_to_string
# from email_utils.send_email import send_mail
# from notification_templates.models import NotificationTemplates
# from partner_company.models import PartnerCompany
# from utils.email_logger import log_email_notification


# def send_support_ticket_email(ticket):
#     """
#     Send email notification to partner company and superadmin when a support ticket is created
    
#     Args:
#         ticket: Ticket object
#     """
#     try:
#         recipients = []
        
#         # Add superadmin email
#         superadmin_email = config("INIT_EMAIL", None)
#         print(f"Superadmin email from settings: {superadmin_email}")  # Debug line
#         if superadmin_email:
#             recipients.append((superadmin_email, "Super Admin", None, None, None))
        
#         # Add partner company email if ticket is created by AD company
#         if ticket.company:
#             # Send to all active partner companies when AD company creates a ticket
#             active_partner_companies = PartnerCompany.objects.filter(
#                 deleted=False, 
#                 status="active"
#             )
#             for partner_company in active_partner_companies:
#                 if partner_company.email:
#                     recipients.append((
#                         partner_company.email, 
#                         partner_company.company_name, 
#                         None, 
#                         partner_company, 
#                         None
#                     ))
        
#         # Add partner company email if ticket is created by partner company directly
#         elif ticket.partner_company:
#             partner_email = ticket.partner_company.email
#             if partner_email:
#                 recipients.append((partner_email, ticket.partner_company.company_name, None, ticket.partner_company, None))
        
#         # Prepare email data
#         email_data = {
#             "ticket_number": ticket.ticket_number,
#             "description": ticket.description,
#             "status": ticket.status,
#             "company_name": ticket.company.name if ticket.company else None,
#             "partner_company_name": ticket.partner_company.company_name if ticket.partner_company else None,
#             "end_client_name": ticket.end_client.name if ticket.end_client else None,
#             "created_by_name": ticket.created_by.get_full_name() if ticket.created_by else "Unknown",
#             "created_at": ticket.created_at.strftime("%Y-%m-%d %H:%M:%S") if ticket.created_at else "",
#             "ticket_topic_name": ticket.ticket_topic.ticket_category if ticket.ticket_topic else "",
#             "admin_url": getattr(settings, 'ADMIN_URL', 'http://127.0.0.1:8000/admin/')
#         }
        
#         # Send emails asynchronously
#         for email, name, related_company, related_partner_company, related_end_client in recipients:
#             # Prepare email data for this recipient
#             recipient_email_data = email_data.copy()
#             recipient_email_data["recipient_name"] = name
#             recipient_email_data["email"] = email  # Add email to data dict for send_mail function
#             recipient_email_data["name"] = name   # Ensure 'name' key exists for send_mail function
            
#             # Send email
#             try:
#                 send_support_ticket_notification_async(
#                     subject=f"New Support Ticket: {ticket.ticket_number}",
#                     template="support-ticket-notification.html",
#                     data=recipient_email_data,
#                     recipients=[email]
#                 )
                
#                 # Log the email
#                 log_email_notification(
#                     recipient_email=email,
#                     subject=f"New Support Ticket: {ticket.ticket_number}",
#                     message_content=f"New support ticket {ticket.ticket_number} created by {ticket.company.name if ticket.company else ticket.partner_company.company_name if ticket.partner_company else 'Unknown'}",
#                     sender_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
#                     email_type="support_ticket",
#                     related_company=related_company,
#                     related_partner_company=related_partner_company,
#                     related_end_client=related_end_client,
#                 )
                
#             except Exception as e:
#                 print(f"Failed to send email to {email}: {str(e)}")
                
#     except Exception as e:
#         print(f"Failed to send support ticket email: {str(e)}")


# # def send_support_ticket_notification(subject, template, data, recipients):
# #     """
# #     Send support ticket notification email to multiple recipients
    
# #     Args:
# #         subject (str): Email subject
# #         template (str): Template name
# #         data (dict): Template context data (must contain 'email' key)
# #         recipients (list): List of email addresses
# #     """
# #     try:
# #         for recipient in recipients:
# #             context = {
# #                 "name": data.get("recipient_name", "User"),
# #                 "email": recipient,
# #                 **data
# #             }
            
# #             # Check for custom notification template
# #             custom_content = None
# #             try:
# #                 notification_template = NotificationTemplates.objects.filter(
# #                     deleted=False,
# #                     title__icontains="support ticket"
# #                 ).first()
                
# #                 if notification_template:
# #                     subject = notification_template.title
# #                     custom_content = notification_template.description
# #                     context["custom_content"] = custom_content
# #             except Exception:
# #                 pass  # Fallback to default template if template lookup fails
            
# #             # Update data with current recipient email for send_mail function
# #             data["email"] = recipient
# #             send_mail(
# #                 subject=subject,
# #                 template=template,
# #                 data=data
# #             )
# #     except Exception as e:
# #         print(f"Failed to send support ticket email: {str(e)}")


# def send_support_ticket_notification_async(subject, template, data, recipients):
#     """
#     Send support ticket notification email asynchronously in background thread
    
#     Args:
#         subject (str): Email subject
#         template (str): Template name
#         data (dict): Template context data
#         recipients (list): List of email addresses
#     """
#     def send_email_background():
#         try:
#             send_support_ticket_notification(subject, template, data, recipients)
#         except Exception as e:
#             print(f"Background email sending failed: {str(e)}")
    
#     # Start background thread
#     thread = threading.Thread(target=send_email_background, daemon=True)
#     thread.start()
