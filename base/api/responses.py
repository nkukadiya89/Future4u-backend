from rest_framework.response import Response


def api_success(data=None, message="OK", status_code=200, meta=None):
    payload = {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
        "errors": [],
        "meta": meta or {},
    }
    return Response(payload, status=status_code)


def api_error(message="Bad request", errors=None, status_code=400, code="bad_request"):
    payload = {
        "success": False,
        "message": message,
        "data": {},
        "errors": errors or [{"code": code, "detail": message}],
        "meta": {},
    }
    return Response(payload, status=status_code)
