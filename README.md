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

Remaining proctoring enhancements:

- Rich tutor-facing violation reports are tracked in Phase 10.
- Strong concurrent-session enforcement is a future security-hardening task.

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
- Tutor billing: `http://127.0.0.1:8000/dashboard/tutor/billing/`
- Student dashboard: `http://127.0.0.1:8000/dashboard/student/`
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

SQLite is used locally when `DATABASE_URL` is empty.

## Background Tasks

Development will use a Python threading backend once the task dispatch layer is implemented.

Production will use Celery and Redis. The production settings fail loudly if Celery is selected but `REDIS_URL` is missing.

Application code should call one internal task dispatch API in future phases instead of calling `threading.Thread` or Celery directly.

## Deployment Direction

The intended production platform is Heroku with:

- Heroku PostgreSQL
- Heroku Redis
- Cloudinary
- M-Pesa Daraja API
- Gunicorn
- Whitenoise
- Celery worker dyno

## Verification

Run:

```powershell
python manage.py check
python manage.py migrate
```

Both commands should pass on a fresh local setup.
