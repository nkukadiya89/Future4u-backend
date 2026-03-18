# @receiver(pre_save)
# def update_pre_save(sender, instance, **kwargs):
#     content_type = ContentType.objects.get_for_model(sender)

#     if sender in SIGNAL_SENDER and instance:
#         pass


# def create_approve_history(sender, instance):
#     content_type = ContentType.objects.get_for_model(sender)

#     if content_type.model == "rfq":
#         company_id = instance.company_id
#         approval_hierarchy = ApprovalHierarchy.objects.filter(
#             content_type=content_type, company_id=company_id
#         ).first()

#     if content_type.model == "quotation":
#         vendor_id = instance.vendor_id
#         approval_hierarchy = ApprovalHierarchy.objects.filter(
#             content_type=content_type, vendor_id=vendor_id
#         ).first()

#     approver_list = ApprovalHierarchyDetail.objects.filter(
#         approval_hierarchy=approval_hierarchy
#     ).order_by("sequence")

#     if approval_hierarchy:
#         approving_history, created = ApprovingHistory.objects.get_or_create(
#             content_type=content_type, rec_id=instance.id, type=approval_hierarchy.type
#         )

#         if created:
#             for approver in approver_list:
#                 ApprovingHistoryDetail.objects.create(
#                     approving_history=approving_history,
#                     approver=approver.approver,
#                     sequence=approver.sequence,
#                 )


# @receiver(post_save)
# def update_post_save(sender, instance, update_fields, created, **kwargs):
#     if sender in SIGNAL_SENDER:
#         create_approve_history(sender, instance)
