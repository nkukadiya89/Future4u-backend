# from django.utils.translation import gettext_lazy as _
# from rest_framework import status
# from rest_framework.exceptions import APIException, _get_error_details


# class ServerError(APIException):
#     status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#     default_detail = _("Invalid input.")
#     default_code = "invalid"

#     def __init__(self, detail, code=None):
#         if detail is None:
#             detail = self.default_detail
#         if code is None:
#             code = self.default_code
#         if "response" in detail:
#             if detail.response is None:
#                 detail = _(
#                     "Connection timed out, Could not get any response from the server."
#                 )

#         # For validation failures, we may collect may errors together, so the
#         # details should always be coerced to a list if not already.
#         if not isinstance(detail, dict) and not isinstance(detail, list):
#             detail = [detail]

#         self.detail = _get_error_details(detail, code)

#     def __str__(self):
#         return six.text_type(self.detail)
