# Aptitude Kenya

Aptitude Kenya is being rebuilt as a professional mobile-first online examination platform for Kenyan tutors, students, and administrators.

The target product supports tutor-created assessments, student credential provisioning, pay-per-student M-Pesa billing, subscriptions, proctoring controls, reminders, calendars, todos, analytics, and Heroku deployment.

## Current Status

The project is in Phase 9: anti-cheating and proctoring. See `DEVELOPMENT_PROCESS.md` for the full tracked roadmap.

Implemented foundation items:

- Local virtual environment support.
- Pinned Python dependencies in `requirements.txt`.
- Environment-driven Django settings.
- Development and production settings modules.
- Heroku `Procfile`.
- Heroku `.python-version`.
- Whitenoise static-file support.
- Local `.env` loading.
- SQLite development database by default.
- PostgreSQL support through `DATABASE_URL`.
- Initial Celery app entrypoint for production workers.

Implemented account items:

- Admin, tutor, and student roles.
- Tutor self-registration.
- Tutor profile and student profile records.
- Tutor-provisioned student accounts.
- Student login using email plus registration number.
- Role-aware dashboard routing.
- Separate portal landing page for returning tutors and students.
- Password reset pages.
- Tutor-side student credential reset.
- Account suspension flag for admin control.

Implemented landing page items:

- Mobile-first public landing page.
- Tutor workflow messaging.
- Student portal messaging.
- KES 5 pay-per-student pricing preview.
- Public billing messaging without exposing payment methods before checkout.
- Anti-cheating and violation policy messaging.
- Contact form and responsive footer.

Implemented tutor workflow items:

- Tutor dashboard overview.
- Classroom creation, editing, and archiving.
- Tutor-owned student creation.
- Classroom-level student creation and assignment.
- CSV/XLSX student bulk import.
- Student search/filtering.
- Student credential reset.
- Classroom-level performance overview placeholder.
- Ownership tests for tutor-only classroom access.

Implemented assessment builder items:

- Assessment types: quiz, assignment, test, CAT, and exam.
- Draft and published assessment states.
- Scheduling, duration, attempts, pass mark, late submission, and result visibility settings.
- Question sections.
- Question types for objective, written, upload, and passage-based assessments.
- Dynamic A-F choices.
- Optional media URL fields ready for Cloudinary integration.
- Reusable question bank.
- CSV/XLSX question import.
- Tutor ownership tests for assessment access and validation.

Implemented billing items:

- Admin-managed pay-per-student pricing with the default KES 5 rate.
- Subscription plans with configurable duration, discounts, and anti-cheating tier labels.
- Tutor subscription records.
- Assessment and subscription invoices.
- Payment records.
- Tutor billing dashboard.
- Admin revenue overview.
- Payment or active subscription gate before publishing paid assessments.
- M-Pesa STK callback reconciliation with duplicate callback protection.
- M-Pesa C2B confirmation endpoint scaffold.
- Development-only payment confirmation for local testing.
- Tests for invoices, subscriptions, publish gating, and callback idempotency.

Remaining payment integration work:

- Connect live Daraja STK Push request signing once sandbox or production credentials are available.
- Complete full C2B validation/reconciliation against provider payloads.
- Run M-Pesa sandbox and production QA before real money is accepted.

Implemented student workflow items:

- Student dashboard with assigned published assessments.
- Assessment grouping for pending, active, overdue, and completed work.
- Calendar-style upcoming assessment list.
- Student-created todos.
- Todo-linked reminders.
- In-app notification center for newly visible assessments.
- Student profile summary.
- Result history controlled by tutor result visibility settings.
- Ownership checks so students only see their own classrooms, todos, reminders, notifications, and results.
- Tests for assignment visibility, dashboard grouping, todos, reminders, and notification actions.

Remaining student workflow integration work:

- Background reminder dispatch is intentionally tracked in Phase 12 with the threading/Celery task abstraction.

Implemented exam-taking items:

- Student assessment start/resume flow from the dashboard.
- Attempt access checks for assignment, publish state, start time, close time, and attempt limits.
- Mobile-first attempt page.
- Countdown timer.
- Question navigation.
- Section-aware question ordering.
- Save answers during an attempt.
- Resume unfinished attempts.
- Auto-submit when the server sees an expired attempt.
- Objective grading for single choice, multiple choice, and true/false questions.
- Written answer storage for tutor review.
- Result page controlled by tutor result visibility settings.
- Tests for attempt access, saving, submission, objective grading, attempt limits, and result redirects.

Remaining exam-taking enhancements:

- Background JavaScript auto-save/API polling for every answer change.
- Rich submit confirmation modal.
- Offline retry/autosync for unstable connections.
- Full manual marking workflow for essays and file uploads.

Implemented proctoring items:

- Per-assessment proctoring rules.
- Copy, paste, cut, right-click, and text-selection blocking.
- Tab switch, window blur, fullscreen exit, and refresh/reload detection.
- Optional fullscreen requirement.
- Violation logging tied to student, assessment, and submission.
- Warning thresholds.
- Auto-submit at violation threshold.
- Auto-disqualification at violation threshold.
- Disqualification status on result pages.
- Admin visibility for proctor logs.
- Tests for proctor settings, violation logging, thresholds, auto-submit, and disqualification.

Important browser limitation:

- Normal browsers cannot fully prevent operating-system screenshots. The platform detects related suspicious behavior such as focus changes and fullscreen exits, but it must not promise perfect screenshot blocking.

## Phase 10 Reports And Analytics

Implemented reporting items:

- Tutor performance overview across classrooms and assessments.
- Classroom reports with student progress, completion, average score, disqualification, and violation counts.
- Assessment reports with pass rate, completion rate, score distribution, question difficulty, and proctoring violation summaries.
- Student report page with personal progress and result history.
- Admin platform analytics for usage, revenue, tutor activity, submissions, and integrity events.
- Native Excel `.xlsx` export and CSV export for assessment reports.
- Printable report pages that can be saved to PDF through the browser print flow.
- Tests for report aggregation, ownership scope, student result visibility, CSV export, and Excel export.

Remaining reporting enhancements:

- Native server-side PDF generation.
- Background generation for very large reports after the Phase 12 task-dispatch layer is in place.
- Strong concurrent-session enforcement is a future security-hardening task.

## Phase 11 Admin Platform Management

Implemented admin operations:

- Custom platform admin console beyond Django admin.
- Tutor and student search, status review, suspension, reinstatement, and tutor verification.
- Invoice, payment, and tutor subscription review.
- Manual invoice paid/cancel actions with audit logging.
- Pay-per-student pricing management.
- Subscription plan management for monthly, quarterly, yearly, discounted, and anti-cheating-tiered plans.
- Contact message review and conversion into support issues.
- Support issue tracking with priority, assignment, status, and resolution notes.
- Platform announcements for tutors, students, or all users.
- Audit log view for admin actions.
- Tests for admin permissions and key operational actions.

Remaining admin enhancements:

- Richer pagination and bulk actions for large production datasets.
- More granular admin permissions if support staff and finance staff need separate access levels.

## Phase 13 QA And Security Hardening

Implemented hardening items:

- Production settings enforce HTTPS redirects, secure cookies, HSTS, no-sniff headers, same-origin referrer policy, and frame denial.
- Django deployment checks pass under production settings with required environment variables.
- CSV/XLSX import forms reject unsupported file extensions and oversized files through `MAX_IMPORT_UPLOAD_SIZE`.
- M-Pesa STK and C2B callbacks reject malformed JSON.
- Optional `MPESA_CALLBACK_TOKEN` can require a shared token in `X-MPESA-CALLBACK-TOKEN` or the callback query string.
- STK callback reconciliation rejects payloads missing `CheckoutRequestID`.
- CSRF enforcement was tested for sensitive admin write actions.
- Student result pages and tutor report pages were covered with data-isolation tests.
- Additional tests cover upload validation, callback validation, callback token enforcement, and result isolation.

Residual production notes:

- Configure a strong `SECRET_KEY`, exact `ALLOWED_HOSTS`, exact `CSRF_TRUSTED_ORIGINS`, `REDIS_URL`, Cloudinary credentials, and M-Pesa credentials on Heroku.
- Use a provider-compatible callback token only if the deployed M-Pesa callback URL can include a token or the provider/proxy can send the configured header.
- Full browser automation is still a later QA enhancement; local HTTP smoke checks are currently used for rendered page verification.

## Dashboard Revamp

Dashboard review and revamp documentation:

- `docs/DASHBOARD_AUDIT.md` records the current dashboard/report issues.
- `docs/DASHBOARD_REVAMP.md` defines the shared layout system, modal pattern, student identity pattern, classroom membership rules, and GitHub documentation expectations.

The revamp starts with tutor and classroom dashboards, then reports, student dashboard, admin console, and assessment builder.

Current revamp progress:

- Tutor dashboard refactored with shared dashboard layout primitives.
- Tutor create classroom and create student forms moved into Bootstrap modals.
- Tutor student listings show registration number as part of the primary student identity.
- Classroom dashboard refactored with modal add/create/import actions.
- Existing tutor-owned students can be added to or removed from a classroom by registration number without creating duplicate accounts.
- Tutor, classroom, assessment, student reports, and assessment exports now include registration numbers in student-facing rows.
- Student dashboard refactored with shared dashboard layout, modal todo creation, assessment calendar, reminders, notifications, and result history.
- Admin console refactored with shared dashboard navigation, professional data tables, status pills, modal plan/pricing and announcement forms, and registration-aware student account rows.

## Local Setup

From the project root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Important local URLs:

- Marketing website: `http://127.0.0.1:8000/`
- Account portal: `http://127.0.0.1:8000/portal/`
- Login/signup form: `http://127.0.0.1:8000/auth/`
- Admin console: `http://127.0.0.1:8000/dashboard/admin/`
- Admin users: `http://127.0.0.1:8000/dashboard/admin/users/`
- Admin billing: `http://127.0.0.1:8000/dashboard/admin/billing/`
- Admin plans/pricing: `http://127.0.0.1:8000/dashboard/admin/plans/`
- Admin support: `http://127.0.0.1:8000/dashboard/admin/contacts/`
- Admin announcements: `http://127.0.0.1:8000/dashboard/admin/announcements/`
- Tutor billing: `http://127.0.0.1:8000/dashboard/tutor/billing/`
- Tutor reports: `http://127.0.0.1:8000/dashboard/tutor/reports/`
- Student dashboard: `http://127.0.0.1:8000/dashboard/student/`
- Student reports: `http://127.0.0.1:8000/dashboard/student/reports/`
- Student attempt pages are opened from active assessments on the student dashboard.

The intended production split is a public website for information and a separate portal domain such as `portal.aptitudekenya.ac.ke` for account access.

If the virtual environment does not exist yet:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Settings

Local development uses:

```text
config.settings.development
```

Production uses:

```text
config.settings.production
```

The default `manage.py`, `asgi.py`, and `wsgi.py` entrypoints point to development settings unless `DJANGO_SETTINGS_MODULE` is explicitly set.

## Environment Variables

Copy `.env.example` to `.env` for local development.

Important variables:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `REDIS_URL`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `MPESA_CONSUMER_KEY`
- `MPESA_CONSUMER_SECRET`
- `MPESA_SHORTCODE`
- `MPESA_PASSKEY`
- `MPESA_CALLBACK_TOKEN`
- `MAX_IMPORT_UPLOAD_SIZE`

SQLite is used locally when `DATABASE_URL` is empty.

## Background Tasks

Application code dispatches background work through `core.tasking.dispatch_task`.

Development uses Python threading by default and does not require Redis. Tests can run tasks inline with `BACKGROUND_TASK_SYNCHRONOUS=True`.

Production uses Celery and Redis by default. The production settings fail loudly if Celery is selected but `REDIS_URL` is missing.

Implemented jobs:

- Email notification dispatch.
- Due reminder dispatch with in-app notifications and email.
- Stale pending payment failure for retry cleanup.
- Assessment report snapshot generation.
- Old task log cleanup.
- Old read notification cleanup.

Admins can view task logs and manually queue operational jobs at `http://127.0.0.1:8000/dashboard/admin/background-jobs/`.

## Deployment Direction

The intended production platform is Heroku with:

- Heroku PostgreSQL
- Heroku Redis
- Cloudinary
- M-Pesa Daraja API
- Gunicorn
- Whitenoise
- Celery worker dyno

Deployment artifacts:

- `Procfile` defines release, web, and worker processes.
- `app.json` documents Heroku add-ons, formation, and required config vars.
- `DEPLOYMENT.md` contains the full Heroku setup and verification checklist.

## Verification

Run:

```powershell
python manage.py check
python manage.py migrate
```

Both commands should pass on a fresh local setup.
