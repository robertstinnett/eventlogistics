# Event Logistics SaaS (Phase 1 Baseline)

Dockerized Django + PostgreSQL baseline for an event/festival logistics SaaS.

## Operations guide
- Full run/use/manage instructions: [OPERATIONS.md](OPERATIONS.md)
- Phase plan and implementation steps: [PHASES.md](PHASES.md)

## Included in this baseline
- Django 5.2 project scaffold with split settings
- Custom email-based user model
- Core apps: users, accounts, plans, events, participants, spaces, finance, dashboard, api
- PostgreSQL, Redis, Mailpit via Docker Compose
- Foundational domain models for events, spaces, participants, and vendor ledger
- Transactional booking service to prevent overbooking

## Quick start
1. Copy environment file:
   - `cp .env.example .env`
2. Build and run services:
   - `docker compose up --build`
3. Create superuser:
   - `docker compose exec web python manage.py createsuperuser`
4. Open app:
   - http://localhost:8000
5. Mail UI (development):
   - http://localhost:8025

## Useful commands
- Run migrations manually: `docker compose exec web python manage.py migrate`
- Create new migrations: `docker compose exec web python manage.py makemigrations`
- Run tests: `docker compose exec -T web python manage.py test --noinput`
- Health check: `curl http://localhost:8000/healthz/`
- Readiness check (includes DB): `curl http://localhost:8000/readyz/`
- Billing page: `http://localhost:8000/billing/`
- Account audit log page: `http://localhost:8000/dashboard/audit-log/`
- Account billing CSV export: `http://localhost:8000/finance/account/ledger/export.csv`
- API token endpoint: `http://localhost:8000/api/token/`
