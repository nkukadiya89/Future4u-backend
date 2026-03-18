# App-by-App Backend Standards Tracker

This tracker is used to roll out backend standards app by app.

## Rollout status

- `company`: baseline done (service-layer API, selectors, indexes, pagination envelope).
- `country`: list endpoint pagination standardized in this pass.
- `currency`: list endpoint pagination standardized in this pass.
- `newsletter`: list endpoint pagination standardized in this pass.
- `activity_log`: list pagination logic fixed and `.all()` usage removed in API querysets.
- `pincode`: pending deeper service extraction and query optimization.
- `subscription`: pending audit-field completion for `PaymentSubscription`.
- `user`: broad exceptions removed in password reset/logout path; larger service extraction still pending.
- `common`, `core`, `bulk_upload`: pending review.

## Automated audit command

Run:

`python manage.py audit_backend_standards`

The command checks each app for:

- `.all()` usage in API/service/query paths
- broad exception handling patterns
- list endpoints missing pagination configuration
- model classes missing audit fields

Current remaining issues (latest audit):

- `activity_log`: missing audit fields on `WhatsAppMessageLog` and `ActivityLog`.
- `company`: broad except in async fallback paths; missing audit fields on `CompanyProfile`.
- `subscription`: missing audit fields on `PaymentSubscription`.
