# Backend Standards

This document defines required backend quality bars for architecture, APIs, performance, and review.

## Backend Coding Standards

- Keep views thin and move domain logic to services/selectors/repositories.
- Do not place business logic in Django signals.
- Enforce `black`, `isort`, and `flake8` in local and CI checks.
- Keep functions below 40 lines where practical; split into helpers when needed.

## Database and Query Optimization

- Add indexes for status/date filter fields and high-use FK filters.
- Do not use `.all()` in production API data paths.
- Use `select_related` and `prefetch_related` for relational reads.
- Include `created_at`, `updated_at`, `created_by`, and `updated_by` in new business tables.

## API Design and Performance

- Paginate every list API.
- Use a consistent response shape: `success`, `message`, `data`, `errors`, `meta`.
- Keep API latency target under `300ms` (p95 target for monitored endpoints).
- Move heavy operations to async workers (Celery tasks/background processing).

## Load and Stress Testing

- Run concurrent user tests for critical APIs.
- Run database stress testing for high-read and high-write workflows.
- Monitor memory and response-time trends during load tests.

## Logging and Monitoring

- Emit structured logs for API requests and errors.
- Keep error tracking enabled in non-local environments.
- Monitor API latency with alerting for threshold breaches.

## AI and Manual Code Review

- Avoid over-abstraction; optimize for maintainability and readability.
- Never swallow exceptions silently.
- Include manual architecture review for major backend changes.
