# Event Logistics - Handoff Notes

Last updated: 2026-04-28

## 1. Purpose

This document is a fast handoff for continuing development from another laptop.

## 2. Current Product State

The app is a Django + Docker event operations platform with these major flows implemented:

- Participant CRUD with vendor/performer/exhibitor edit support
- Space type CRUD (create, edit, delete)
- Guarded space type deletion with required re-assignment when bookings exist
- Space booking create, quantity edit, and unassign/remove
- Automatic vendor ledger entries for space assignment and removal deltas
- Event/vendor finance ledger screens and CSV exports
- Dashboard KPIs for occupancy and billing totals
- Audit log for account-scoped operational actions
- Modernized UI pass across core pages

## 3. Important Recent Changes

### Spaces and Ledger Automation

- Booking assignment now writes a ledger charge automatically
  - Note pattern: "Space assignment: <space type> x <qty>"
- Booking quantity decrease writes a negative charge for removed units
  - Note pattern: "Space removal: <space type> x <qty>"
- Full booking unassign writes a negative charge and deletes booking
- Booking quantity increase writes charge only for the incremental quantity

### Vendor Edit Page Enhancements

From vendor edit page:

- Can view current assigned spaces
- Can assign a new space directly
- Can delete an assigned space directly

These actions stay on vendor edit page and still use the shared booking/unassign logic.

## 4. Key Files To Know

- apps/spaces/services.py
- apps/spaces/views.py
- apps/spaces/forms.py
- apps/spaces/tests.py
- apps/participants/views.py
- templates/participants/form.html
- apps/participants/tests.py
- apps/api/tests.py
- OPERATIONS.md

## 5. Validation Status (recent)

The following test slices were passing at handoff time:

- apps/spaces.tests
- apps/api.tests
- apps/participants.tests

And Django checks were clean:

- python manage.py check

## 6. Bring-Up On New Laptop

1. Clone repo and enter project directory.
2. Create environment file.
3. Build and start containers.
4. Apply migrations.
5. Run checks and tests.

Use these commands:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py test
```

## 7. Quick Smoke Paths

- /
- /events/
- /participants/event/<event_id>/
- /participants/event/<event_id>/vendors/<vendor_id>/edit/
- /spaces/event/<event_id>/
- /finance/event/<event_id>/ledger/
- /dashboard/event/<event_id>/

## 8. Known Follow-Ups

- Consider updating OPERATIONS.md section 6.4 to explicitly mention:
  - space assignment/removal available from vendor edit page
  - automatic ledger charge/credit behavior tied to booking changes
- If desired, add booking quantity edit controls directly inside vendor edit assignment list (currently assignment + delete are available there; quantity edit is available in spaces booking flow).

## 9. Transfer Checklist

Before switching laptops:

- Commit all local changes
- Push branch to remote
- Confirm new laptop can run migrate/check/test
- Keep this HANDOFF.md updated after major feature changes
