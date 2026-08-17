# Wardline — Hospital Management ERP

A multi-tenant hospital management SaaS: one Django app serving many hospitals, each on
its own subdomain with fully isolated data, from patient registration through OPD,
clinical notes, pharmacy, lab, billing, wards, and role-based dashboards.

**New here?** See **[USAGE.md](USAGE.md)** for the full step-by-step setup and a walkthrough
of every module.

## Tech stack

- **Backend:** Django 6.1, Python 3.14
- **Frontend:** Django templates + Tailwind CSS (CLI build for the app, CDN for the
  marketing site) + Alpine.js + htmx — no separate JS framework/SPA
- **Database:** PostgreSQL (shared-schema multi-tenancy — every tenant row carries a
  `hospital` FK, auto-scoped by `apps.core.models.TenantAwareManager`; see
  [`apps/core/middleware.py`](apps/core/middleware.py) for how a subdomain resolves to a
  hospital and switches the active urlconf)
- **PDF reports:** xhtml2pdf (lab reports)
- **Background jobs:** Celery + Redis are configured in settings but not yet wired to any
  task — everything currently runs synchronously

## Repository layout

```text
apps/
  core/        shared tenant-isolation machinery (middleware, base models, permissions)
  tenants/     platform side: Hospital/Plan registry, signup flow, super-admin console
  users/       custom User model (role + hospital FK), auth, password reset
  marketing/   public landing page (isolated design system, Tailwind CDN)
  dashboard/   role-based dashboard + Chart.js widgets
  patients/    registration, MRN generation, search
  appointments/  doctor schedules, booking, OPD token queue
  clinical/    consultations, vitals, prescriptions, lab orders
  pharmacy/    drug catalog, stock, dispensing
  lab/         test catalog, sample collection, results, PDF reports
  billing/     invoices, payments
  wards/       ward/room/bed master, admissions, discharge
config/        settings (base/dev/prod/test/pythonanywhere), urls (public + tenant)
templates/     base_public.html / base_console.html / base_tenant.html + per-app templates
static/src/    Tailwind CLI input; static/css/output.css is the generated (gitignored) build
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
npm install && npm run build:css
cp .env.example .env   # edit DATABASE_URL etc. if needed
python manage.py migrate
python manage.py seed_plans        # Starter/Growth/Enterprise pricing tiers
python manage.py createsuperuser   # platform owner account
python manage.py runserver
```

Then visit `http://localhost:8000/` for the marketing site, or
`http://localhost:8000/platform/` (logged in as the superuser) for the platform console.
Full walkthrough — signing up a hospital, logging in as its admin, and using every
module — is in **[USAGE.md](USAGE.md)**.

## Local database

This project expects Postgres reachable at the `DATABASE_URL` in `.env`. In this
environment that's a Docker Postgres instance (`postgres_db`) — user `root`, password
`root1234`, database `hospital_erp`.

## Production notes

- `config/settings/prod.py` — Postgres, HTTPS/HSTS enforced, SMTP email.
- `config/settings/pythonanywhere.py` — SQLite instead of Postgres for PythonAnywhere's
  free/hacker tiers. This is safe under this app's shared-schema tenancy (isolation is
  enforced by `TenantAwareManager` regardless of DB engine, not by Postgres schemas), but
  SQLite serializes writes — move to `prod.py` before real concurrent load.
- Before production: switch Tailwind's marketing site off the CDN build, put a real
  payment gateway behind tenant billing (currently stubbed), and review
  `SECRET_KEY`/`ALLOWED_HOSTS`/`SESSION_COOKIE_SECURE`.
