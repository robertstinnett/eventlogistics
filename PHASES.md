# Event Logistics SaaS Phases and Steps

## Phase 1 - Baseline Platform (Completed)
1. Core Django + PostgreSQL containerized stack.
2. Custom user model and account provisioning.
3. Event, participant, space, and dashboard domains.
4. No-overbooking transactional booking service.
5. API endpoints for core logistics workflows.

## Phase 2 - Operational Workflows (In Progress)
1. Add event finance ledger UI and permissions. (Completed)
2. Add health and readiness monitoring endpoints. (Completed)
3. Add CI automation for checks/tests. (Completed)
4. Expand integration test coverage for tier rules, booking auth, and dashboard metrics. (Completed)

## Phase 3 - Team and Billing Expansion (Next)
1. Account invitation acceptance flow and member role management screens. (Completed)
2. Paid tier upgrade/downgrade workflow and plan enforcement controls. (Completed)
3. Billing reports export (CSV) per event and per account. (Completed)

## Phase 4 - Production Hardening (Next)
1. API token auth option for integrations. (Completed)
2. Audit log for key operational changes. (Completed)
3. Deployment profile with production settings checklist and zero-downtime migration steps.
