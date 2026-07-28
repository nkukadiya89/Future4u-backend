from rest_framework.routers import DefaultRouter

from employee.views import (
    AddEmployeeViewSet,
    BulkEmployeeViewSet,
    EmployeeArchiveViewSet,
    EmployeeRestoreViewSet,
    EmployeeStatusViewSet,
)

employee_router = DefaultRouter()
employee_router.register("employee", AddEmployeeViewSet, basename="employee")
employee_router.register(
    "employee-status", EmployeeStatusViewSet, basename="employee_status"
)
employee_router.register(
    "employee-archive", EmployeeArchiveViewSet, basename="employee_archive"
)
employee_router.register(
    "employee-restore", EmployeeRestoreViewSet, basename="employee_restore"
)
employee_router.register(
    "employee-bulk-upload", BulkEmployeeViewSet, basename="employee_bulk_upload"
)
