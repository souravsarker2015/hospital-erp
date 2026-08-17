# Using Wardline — step by step

This walks through setting the project up from a clean checkout, then using every module
as each role would. Screens referenced below assume you're running locally at
`localhost:8000`.

## 1. Prerequisites

- Python 3.12+ (built against 3.14.6)
- Node.js 18+ (for the Tailwind CLI build)
- PostgreSQL 14+, reachable and matching the credentials in your `.env`

## 2. First-time setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt

npm install
npm run build:css          # compiles static/src/input.css -> static/css/output.css

cp .env.example .env       # adjust DATABASE_URL etc. if your Postgres differs
python manage.py migrate
python manage.py seed_plans        # creates the Starter/Growth/Enterprise plans
python manage.py createsuperuser   # your platform-owner login (leave "hospital" unset)
```

`manage.py` defaults to `config.settings.dev`, which reads `.env` automatically.

## 3. Run it

```bash
python manage.py runserver
```

Leave a second terminal open running `npm run watch:css` while you work on templates —
it rebuilds `output.css` on save. Without it, new Tailwind classes you add won't appear
until you re-run `npm run build:css`.

Multi-tenancy is subdomain-based: `localhost:8000` is the public/marketing site, and each
hospital gets `<subdomain>.localhost:8000`. Modern browsers resolve any `*.localhost`
hostname to `127.0.0.1` automatically — no `/etc/hosts` editing needed.

## 4. Tour the public site

Visit `http://localhost:8000/`:

- **`/`** — the marketing/landing page (features, pricing pulled live from the `Plan`
  table, FAQ).
- **`/signup/`** — pick a plan, then fill in the hospital + first-admin form. Submitting
  this creates the `Hospital`, a trial `Subscription`, and your Admin user in one step,
  then shows you the login link for your new subdomain
  (`http://<your-subdomain>.localhost:8000/accounts/login/`).
- **`/accounts/login/`** — login for platform-side (superuser) accounts only. Hospital
  staff log in on their own subdomain instead, at
  `http://<subdomain>.localhost:8000/accounts/login/`.

## 5. The platform console

Log in at `/accounts/login/` with the superuser you created in step 2, then visit
**`/platform/`**. This lists every hospital on the platform with search, status/plan
filters, and one-click **Suspend/Activate** — suspending a hospital immediately 404s its
entire subdomain for staff and patients alike.

Django's own admin is also available at **`/admin/`** (same superuser) if you need
lower-level access — e.g. editing a `Plan`, or creating additional staff accounts for a
hospital (see step 7).

## 6. Sign up your first hospital

1. Go to `/signup/`, pick a plan (**Growth** unlocks the Lab module; **Enterprise** also
   unlocks Wards).
2. Fill in the hospital name, a subdomain (e.g. `citycare`), your name, a username and
   password. This account becomes that hospital's **Admin**.
3. You'll land on a success page with a link to
   `http://citycare.localhost:8000/accounts/login/` — click it and log in.

You're now on the hospital's own dashboard, scoped entirely to that hospital's data.

## 7. Add staff for the hospital

There's currently no self-service "invite a colleague" screen — the fastest path is the
Django admin, as the platform superuser:

1. On the **bare domain**, go to `/admin/login/` and log in as your superuser.
2. Under **Users**, click **Add user**, fill in username/password.
3. In the **Hospital ERP** section of that user's edit page, set **Hospital** to the
   hospital they belong to and **Role** to one of: Admin, Doctor, Nurse, Receptionist,
   Pharmacist, Lab Technician, Accountant.
4. They log in at `http://<subdomain>.localhost:8000/accounts/login/`.

Create at least one **Doctor** now — the next steps need one.

## 8. Walk through a full patient visit

Do these in order; each step depends on data from the previous one. All URLs below are
on your hospital's subdomain (e.g. `citycare.localhost:8000`), and the sidebar links to
each of these directly.

### a. Register a patient — *Patients*

`Patients → Register Patient`. Fill in demographics, blood group, allergies, emergency
contact. On save you get an auto-generated MRN — the first 3 letters of the hospital's
subdomain plus a 6-digit sequence, e.g. `CIT-000001`, independent per hospital. The
patient list supports instant search by name, phone, or MRN.

### b. Set a doctor's schedule — *Appointments → Doctor Schedules* (Admin only)

Add a weekly availability block for your doctor (weekday, start/end time, slot length).
Booking will only offer slots inside a schedule block that don't already have an
appointment.

### c. Book an appointment — *Appointments → Book Appointment*

Search for the patient you registered, pick the doctor and date, choose a generated time
slot (this is where double-booking is prevented — an already-taken slot simply won't be
offered), add a reason, submit. You'll land back on the **OPD Queue** with a token
number.

### d. Run the visit — *Appointments (queue)*

On the queue: **Check In** the patient, then a nurse can **Record Vitals**. The doctor
clicks **Start Consultation**, which opens the clinical workspace and moves the
appointment to *In Consultation*.

### e. Consultation, prescription, lab order — *Clinical*

On the consultation screen: fill in chief complaint/history/examination/diagnosis
(optional ICD-10 code), add prescription line items (drug/dosage/frequency/duration) and
lab orders (free-text test name — matched to the catalog later), then **Complete
Consultation**. This locks the record and marks the appointment *Completed*. You can
print the prescription from here or from the queue.

### f. Dispense the prescription — *Pharmacy*

First add the prescribed drug to the catalog if it's not there yet (`Pharmacy → Add
Drug`, set a **unit price** — needed for billing later), then **Stock In** a batch
(batch number, expiry date, quantity). Go to `Pharmacy → Dispense Queue`, find the
patient's pending item, pick the drug/batch, and dispense — stock decrements
automatically.

### g. Process the lab order — *Lab*

Add the ordered test to the catalog if needed (`Lab → Add Test`, set a **price**), then
`Lab → Sample Queue` → **Collect Sample** (matches the order to the catalog test) →
**Enter Result**. Once entered, a **View Report** link produces a real PDF.

### h. Bill the visit — *Billing*

`Billing → Billing Queue` lists completed, uninvoiced visits. **Generate Invoice**
auto-combines the dispensed drug and the priced lab result as line items. If you've set
up a *Consultation*-category item in `Billing → Service Catalog`, it's added
automatically too (only when exactly one exists — otherwise add it manually on the
invoice). Record a payment (cash/card/insurance) — partial payments are allowed and the
invoice status updates automatically. **Print** gives a receipt.

### i. Admit to a ward (Growth/Enterprise plans) — *Wards*

Set up the hierarchy once: `Wards → Manage Wards` → add a ward → add a room → add a bed
(with a nightly rate). Back on the **Ward Board**, click an available bed to admit a
patient (same patient-search widget as booking); click an occupied bed to see the
admission and **Discharge** with a summary.

### j. Check the dashboard

Each role sees different tiles on `/` (the dashboard): Admin gets today's appointments,
revenue, bed occupancy, low stock, pending labs, and staff count, plus a 7-day revenue
chart and a bed-occupancy chart. Doctor, Nurse, Receptionist, Pharmacist, Lab Technician,
and Accountant each see the numbers relevant to their own work.

## 9. Role reference

| Role | Can do |
| --- | --- |
| Admin | Everything below, plus staff/schedule/ward/service-catalog setup |
| Doctor | Consultations, prescriptions, lab orders; view/manage their own queue |
| Nurse | Register/edit patients, book appointments, record vitals, admissions |
| Receptionist | Register/edit patients, book appointments, billing |
| Pharmacist | Drug catalog, stock in/adjust, dispensing |
| Lab Technician | Test catalog, sample collection, result entry |
| Accountant | Billing: invoices, payments, service catalog |

Every role can *view* patients, appointments, and print prescriptions/invoices/reports;
the table above is who can additionally *create or change* things in that area.

## 10. Everyday commands

```bash
python manage.py makemigrations   # after changing any model
python manage.py migrate
npm run watch:css                 # while editing templates
python manage.py collectstatic    # before a production deploy
python manage.py test             # if/when a test suite is added
```

## 11. Troubleshooting

- **A subdomain gives 404 for everything.** The hospital was suspended (via
  `/platform/`), the subdomain is misspelled, or you're using a hostname that doesn't end
  in `.localhost` — the bare `PLATFORM_DOMAIN` in `.env` must match what you type in the
  browser.
- **Styles look broken / new classes don't show up.** Run `npm run build:css` (or keep
  `npm run watch:css` running). The marketing site is CDN-based Tailwind and doesn't need
  this; every other page uses the compiled `static/css/output.css`.
- **Signup page shows no plans.** Run `python manage.py seed_plans`.
- **Can't reach `/admin/` or `/platform/` from a hospital subdomain.** That's
  intentional — both are only wired into the public urlconf. Use the bare domain.
- **A logged-in hospital user can authenticate on the bare domain but sees nothing
  useful.** Also expected — staff accounts belong to one hospital's subdomain; the bare
  domain is for platform staff and the signup flow.
