from rest_framework.views import exception_handler

from base.api.responses import api_error


def standardized_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return api_error(
            message="Internal server error",
            errors=[{"code": "server_error", "detail": "Unexpected server error"}],
            status_code=500,
            code="server_error",
        )

    detail = response.data
    errors = detail if isinstance(detail, list) else [detail]
    return api_error(
        message="Request failed",
        errors=[{"code": str(response.status_code), "detail": errors}],
        status_code=response.status_code,
        code="request_failed",
    )
