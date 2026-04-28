# Event Logistics SaaS Operations Guide

This guide covers how to run, use, and manage the website in day-to-day operations.

## 1. Prerequisites

- Docker Engine and Docker Compose plugin installed.
- Open ports:
  - 8000 (web)
  - 5432 (PostgreSQL)
  - 6379 (Redis)
  - 1025 and 8025 (Mailpit)

## 2. First-Time Setup

1. Create local environment file:

```bash
cp .env.example .env
```

2. Build and start services:

```bash
docker compose up --build -d
```

3. Apply database migrations:

```bash
docker compose exec -T web python manage.py migrate --noinput
```

4. Create an admin account:

```bash
docker compose exec web python manage.py createsuperuser
```

5. Open apps:
- Main site: http://localhost:8000
- Django admin: http://localhost:8000/admin/
- Mailpit UI: http://localhost:8025

## 3. Daily Startup and Shutdown

Start stack:

```bash
docker compose up -d
```

Stop stack (keep data):

```bash
docker compose down
```

Stop stack and remove volumes (destructive):

```bash
docker compose down -v
```

## 4. Health Checks and Status

Check service status:

```bash
docker compose ps
```

Check app health quickly:

```bash
curl -i http://localhost:8000/
```

Lightweight health endpoint:

```bash
curl -s http://localhost:8000/healthz/
```

Readiness endpoint (verifies database connectivity):

```bash
curl -s -i http://localhost:8000/readyz/
```

Run Django system checks:

```bash
docker compose exec -T web python manage.py check
```

## 5. Logs and Troubleshooting

Follow all service logs:

```bash
docker compose logs -f
```

Follow web logs only:

```bash
docker compose logs -f web
```

Common issues:
- Migrations missing:
  - Run: docker compose exec -T web python manage.py makemigrations
  - Then: docker compose exec -T web python manage.py migrate --noinput
- Database container not healthy:
  - Run: docker compose logs db
  - Confirm POSTGRES settings in .env
- Login/API authentication confusion:
  - UI routes redirect to login when unauthenticated.
  - API routes with session or token auth return 401 or 403 depending on endpoint/auth challenge handling.

## 6. Core User Workflows (How To Use)

### 6.1 Register and Sign In
- Go to /accounts/register/
- Create account and organization name.
- New accounts are provisioned to Free Tier.
- Sign in at /accounts/login/.

### 6.2 Create Events
- Go to /events/ and choose Create Event.
- Fill name, schedule, and status.
- Free Tier enforces 1 active/upcoming event at a time.

### 6.3 Manage Participants
- From event details, open Participants.
- Add vendors, performers, and exhibitors.

### 6.4 Manage Space Inventory and Assignments
- Open Spaces from an event.
- Create Space Types with inventory and pricing.
- Assign spaces to vendors.
- Overbooking is blocked by transactional inventory checks.

### 6.5 Use the Dashboard
- Open Dashboard from event details.
- Review occupancy, participant counts, billed/paid totals, and outstanding balance.

### 6.6 API Usage
- Base path: /api/
- Token endpoint: GET or POST /api/token/
- Space booking endpoint: POST /api/space-bookings/
- Supports session authentication and token authentication.
- Requires authentication and manager/owner permissions on the event account.

Integration token flow:
- Sign in through the web app.
- GET /api/token/ to fetch or create an integration token.
- POST /api/token/ to rotate the current token.
- Send header: Authorization: Token <your-token>

Example payload:

```json
{
  "event_id": 1,
  "space_type_id": 2,
  "vendor_id": 3,
  "quantity": 1
}
```

Example token-auth request:

```bash
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/events/
```

### 6.7 Review Operational Audit Log
- Open /dashboard/audit-log/ from top navigation after signing in.
- Scope is account-local; users only see entries for their own primary account.
- Latest 200 entries are shown with actor, action, event, target, and details.
- Typical tracked actions include:
  - team.invitation.created, team.invitation.accepted, team.membership.role_changed
  - billing.plan.changed
  - finance.ledger_entry.created
  - event.created
  - participant.vendor.created, participant.performer.created, participant.exhibitor.created
  - space.type.created, space.booking.created
  - api.token.issued, api.token.fetched, api.token.rotated

### 6.8 Manage Vendor Ledger
- Open an event and click Manage Ledger.
- Add charge, payment, or adjustment entries for event vendors.
- Use ledger totals to reconcile billed, paid, and outstanding balances.

### 6.9 Manage Team Members
- Open Team in the top navigation.
- Create invitations with Manager or Viewer role.
- Share acceptance URL with the invited user.
- Account owner can update existing member roles.

### 6.10 Manage Billing and Plan
- Open Billing in the top navigation.
- Review current plan, billing cycle, and active/upcoming event usage.
- Account owner can upgrade or downgrade plans and set monthly/yearly billing cycle.
- Downgrades are blocked when active/upcoming event count exceeds the target plan limit.
- Event creation plan limits are enforced in both UI and API workflows.

### 6.11 Export Billing CSV Reports
- Open an event ledger and use Export Event CSV to download event-only ledger entries.
- Use Export Account CSV to download ledger entries across all events in the current account.
- CSV columns: event_id, event_name, vendor_id, vendor_name, entry_type, amount, note, created_at.
- Event CSV export is restricted to users who can manage that event account.

## 7. Management Tasks

Create migrations after model changes:

```bash
docker compose exec -T web python manage.py makemigrations
docker compose exec -T web python manage.py migrate --noinput
```

Run test suite:

```bash
docker compose exec -T web python manage.py test
```

Open Django shell:

```bash
docker compose exec web python manage.py shell
```

Collect static files (if needed):

```bash
docker compose exec -T web python manage.py collectstatic --noinput
```

## 8. Data Backup and Restore

Backup PostgreSQL:

```bash
docker compose exec -T db pg_dump -U eventlogistics eventlogistics > backup.sql
```

Restore PostgreSQL:

```bash
cat backup.sql | docker compose exec -T db psql -U eventlogistics -d eventlogistics
```

## 9. Release and Change Procedure

1. Pull latest code.
2. Rebuild images:

```bash
docker compose build
```

3. Start services:

```bash
docker compose up -d
```

4. Run migrations:

```bash
docker compose exec -T web python manage.py migrate --noinput
```

5. Run checks and tests:

```bash
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py test
```

6. Smoke test key routes:

```bash
for p in / /healthz/ /readyz/ /accounts/login/ /accounts/register/ /events/ /api/events/; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000$p)
  echo "$p $code"
done
```

## 10. Security and Access Basics

- Use strong admin passwords and rotate regularly.
- Keep .env out of version control.
- Restrict who can access database and redis ports outside development.
- Review Django admin users and permissions periodically.
