# Aptitude Kenya

Aptitude Kenya is being rebuilt as a professional mobile-first online examination platform for Kenyan tutors, students, and administrators.

The target product supports tutor-created assessments, student credential provisioning, pay-per-student M-Pesa billing, subscriptions, proctoring controls, reminders, calendars, todos, analytics, and Heroku deployment.

## Current Status

The project is in Phase 1: project rescue and foundation. See `DEVELOPMENT_PROCESS.md` for the full tracked roadmap.

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
