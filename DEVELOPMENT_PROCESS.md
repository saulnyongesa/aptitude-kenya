# Aptitude Kenya Development Process

This document is the project tracker for rebuilding Aptitude Kenya into a professional mobile-first online examination SaaS platform. Every major feature must pass through these steps before the project is considered complete.

Status key:

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete
- `[!]` Blocked

## Engineering Rules

- Every feature must include clear models, views/services, templates or API endpoints, validation, permissions, and tests where practical.
- Keep the marketing website and account portal separate. The public site explains the product; the portal is the uncluttered entry point for tutors and students.
- Every important function, service, model, and payment/proctoring workflow must be documented with maintainable docstrings or short comments explaining business intent.
- Keep business logic out of templates. Use services, model methods, managers, or dedicated modules.
- Use mobile-first templates and test small-screen workflows first.
- Use environment variables for secrets and deployment-specific settings.
- Do not store classroom passwords, payment secrets, or sensitive tokens in plain text.
- Tutor data must be isolated from other tutors. Students must only access assigned work.
- No phase should be skipped while previous required tasks are unfinished.

## Background Task Strategy

During local development, background work will use Python threading because Redis and Celery setup may be unreliable on the development machine.

In production, the same task interface must switch automatically to Celery with Redis when the correct environment variables are present.

Required design:

- Create one internal task dispatch API, for example `core.tasks.dispatch_task(name, *args, **kwargs)`.
- In development, dispatch work using a safe thread wrapper.
- In production, dispatch work using Celery workers and Redis.
- Application code must never call `threading.Thread` or Celery directly outside the task dispatch layer.
- The task layer must support email/SMS notifications, payment verification retries, reminders, report generation, and cleanup jobs.
- The deployment must fail loudly if production mode is enabled but Redis/Celery settings are missing.

Suggested behavior:

```text
APP_ENV=development -> Python threading backend
APP_ENV=production  -> Celery + Redis backend
```

## Phase 1: Project Rescue And Foundation

- [x] Remove committed `__pycache__` and `.pyc` files.
- [x] Expand `.gitignore` for Python, Django, environment files, logs, media, and local tooling.
- [x] Add `requirements.txt`.
- [x] Add `.env.example`.
- [x] Split Django settings into base, development, and production settings.
- [x] Move `SECRET_KEY`, `DEBUG`, database, Cloudinary, M-Pesa, Redis, and email settings to environment variables.
- [x] Configure PostgreSQL for production and SQLite or local PostgreSQL for development.
- [x] Add Heroku-ready `Procfile`.
- [x] Add Heroku `.python-version`.
- [x] Add Whitenoise or equivalent static file support.
- [x] Confirm `python manage.py check` passes.
- [x] Confirm migrations run from a fresh database.
- [x] Document local setup in `README.md`.

Exit gate:

- [x] A new developer can clone, create a virtual environment, install requirements, migrate, and run the app.

## Phase 2: Core Accounts And Roles

- [x] Redesign the custom user model for admin, tutor, and student roles.
- [x] Add `TutorProfile`.
- [x] Add `StudentProfile`.
- [x] Add school registration number support.
- [x] Add phone number support for tutors and payment records.
- [x] Add role-based permissions.
- [x] Add tutor self-registration.
- [x] Add dedicated account portal landing page for returning tutors and students.
- [x] Add admin-created or tutor-provisioned student accounts. Bulk import remains tracked in Phase 4.
- [x] Allow student login using tutor-provided credentials.
- [x] Add password reset and credential reset flows.
- [x] Add account suspension/deactivation.
- [x] Add tests for role permissions and login flows.

Exit gate:

- [x] Admin, tutor, and student accounts work separately and cannot access each other’s private areas.

## Phase 3: Professional Landing Page

- [x] Design a polished mobile-first landing page.
- [x] Clearly explain tutor value: create exams, assign students, pay per student, track results.
- [x] Clearly explain student value: easy login, mobile tests, reminders, results.
- [x] Keep public payment messaging generic; supported payment methods appear only during checkout.
- [x] Include anti-cheating and integrity messaging.
- [x] Add pricing preview: pay per student/test and subscription plans.
- [x] Add contact/lead capture form.
- [x] Add responsive navigation and footer.
- [x] Add call-to-action buttons for tutor registration and login.
- [x] Separate public marketing CTAs from the account portal entry point.
- [x] Test layout on mobile, tablet, and desktop.

Exit gate:

- [x] The first page looks credible enough for schools and tutors to trust the platform.

## Phase 4: Tutor Dashboard And Classroom Management

- [x] Build tutor dashboard.
- [x] Add classroom creation.
- [x] Add class editing and archiving.
- [x] Add one-by-one student creation.
- [x] Add bulk student import from CSV/Excel.
- [x] Add student credential generation.
- [x] Add credential reset.
- [x] Add student list filtering/search.
- [x] Add classroom-level performance overview.
- [x] Add tests for tutor ownership rules.

Exit gate:

- [x] A tutor can create classes, add students, and prepare a group for assessment.

## Phase 5: Assessment Builder

- [ ] Support assessment types: quiz, assignment, test, CAT, and exam.
- [ ] Add assessment drafts.
- [ ] Add scheduling: start time, end time, duration.
- [ ] Add marks, pass mark, attempts, late submission, and result visibility settings.
- [ ] Add CKEditor for rich question editing.
- [ ] Add Cloudinary image uploads for questions and explanations.
- [ ] Add question types: single choice, multiple choice, true/false, short answer, essay, file upload, and passage-based questions.
- [ ] Add dynamic choices.
- [ ] Add question sections.
- [ ] Add random question order.
- [ ] Add random answer order.
- [ ] Add bulk upload from CSV/Excel.
- [ ] Add question bank and reusable questions.
- [ ] Add tests for assessment creation and validation.

Exit gate:

- [ ] A tutor can build a professional assessment without developer help.

## Phase 6: Billing, Pricing, And M-Pesa

- [ ] Add admin-managed pay-per-student price, default `KES 5`.
- [ ] Add subscription plans.
- [ ] Support monthly, three-month, quarterly, and yearly subscription durations.
- [ ] Support discounted longer-term subscriptions.
- [ ] Support subscription tiers based on enabled anti-cheating controls.
- [ ] Support cheaper subscriptions for assessments without anti-cheating controls.
- [ ] Add tutor subscription records.
- [ ] Add invoices.
- [ ] Add payment records.
- [ ] Add M-Pesa STK Push.
- [ ] Add M-Pesa C2B.
- [ ] Add callback endpoints.
- [ ] Add duplicate callback protection.
- [ ] Add payment status checks.
- [ ] Add failed payment handling.
- [ ] Add tutor billing dashboard.
- [ ] Add admin revenue dashboard.
- [ ] Require payment or active subscription before publishing paid assessments.
- [ ] Add tests for payment state transitions.

Exit gate:

- [ ] Tutors can pay per test/student or use subscriptions, and assessments unlock only after valid payment.

## Phase 7: Student Dashboard, Calendar, Reminders, And Todos

- [ ] Build student dashboard.
- [ ] Show pending, active, overdue, and completed assessments.
- [ ] Add calendar view.
- [ ] Add reminders.
- [ ] Add todos.
- [ ] Add notification center.
- [ ] Add student profile.
- [ ] Add result history.
- [ ] Add feedback visibility based on tutor settings.
- [ ] Add background reminder dispatch through the task layer.
- [ ] Add tests for student assignment visibility.

Exit gate:

- [ ] A student can see what they need to do, when it is due, and what they already completed.

## Phase 8: Exam-Taking Engine

- [ ] Build mobile-first test-taking interface.
- [ ] Add countdown timer.
- [ ] Add answer auto-save.
- [ ] Add question navigation.
- [ ] Add section navigation.
- [ ] Add submit confirmation.
- [ ] Add auto-submit on timeout.
- [ ] Add network interruption handling.
- [ ] Add resume rules based on tutor settings.
- [ ] Add grading for objective questions.
- [ ] Add manual marking for essays/file uploads.
- [ ] Add result calculation.
- [ ] Add tests for submissions, attempts, timing, and grading.

Exit gate:

- [ ] Students can take assessments reliably on mobile and desktop.

## Phase 9: Anti-Cheating And Proctoring

- [ ] Add per-assessment proctoring rules.
- [ ] Disable copy.
- [ ] Disable paste.
- [ ] Disable right click.
- [ ] Disable text selection.
- [ ] Detect tab switching.
- [ ] Detect window blur.
- [ ] Detect fullscreen exit.
- [ ] Require fullscreen where enabled.
- [ ] Detect refresh/reload attempts.
- [ ] Detect multiple active sessions where practical.
- [ ] Log violations with timestamps.
- [ ] Add warning thresholds.
- [ ] Add auto-submit option.
- [ ] Add auto-disqualification option.
- [ ] Add tutor violation reports.
- [ ] Add admin violation visibility.
- [ ] Document browser limitations, especially screenshot prevention.
- [ ] Add tests for violation thresholds and disqualification.

Important limitation:

- [ ] Normal web browsers cannot fully prevent operating-system screenshots. The system should discourage, detect related focus changes where possible, watermark test pages, and log suspicious activity, but it must not promise perfect screenshot blocking.

Exit gate:

- [ ] Tutors can configure exam integrity rules and the system enforces them consistently.

## Phase 10: Reports And Analytics

- [ ] Add tutor reports.
- [ ] Add student reports.
- [ ] Add class performance analytics.
- [ ] Add question difficulty analysis.
- [ ] Add completion-rate reporting.
- [ ] Add score distribution.
- [ ] Add violation reporting.
- [ ] Add export to Excel.
- [ ] Add export to PDF.
- [ ] Add printable reports.
- [ ] Add admin platform analytics.
- [ ] Generate heavy reports through the task layer.

Exit gate:

- [ ] Tutors and admins can understand performance, usage, and integrity from dashboards and exports.

## Phase 11: Admin Platform Management

- [ ] Build admin dashboard beyond Django admin.
- [ ] Manage tutors.
- [ ] Manage students.
- [ ] Manage subscriptions.
- [ ] Manage pricing.
- [ ] Manage payments.
- [ ] Manage announcements.
- [ ] Manage contact messages.
- [ ] Manage support issues.
- [ ] View audit logs.
- [ ] View platform usage.
- [ ] Suspend abusive accounts.

Exit gate:

- [ ] The platform can be operated by a non-developer administrator.

## Phase 12: Notifications And Background Jobs

- [ ] Implement task dispatch abstraction.
- [ ] Implement development threading backend.
- [ ] Implement production Celery backend.
- [ ] Add email notification service.
- [ ] Add reminder scheduling.
- [ ] Add payment retry/status jobs.
- [ ] Add report generation jobs.
- [ ] Add cleanup jobs.
- [ ] Add task logging.
- [ ] Add failure handling.
- [ ] Add tests for task dispatch selection.

Exit gate:

- [ ] Development works without Redis, and production uses Redis/Celery automatically.

## Phase 13: Testing, QA, And Security Hardening

- [ ] Add unit tests for models and services.
- [ ] Add integration tests for auth, assessments, payments, submissions, and proctoring.
- [ ] Add permission tests.
- [ ] Add form validation tests.
- [ ] Add payment callback tests.
- [ ] Add browser tests for key flows where practical.
- [ ] Run Django deployment checks.
- [ ] Review CSRF and authentication.
- [ ] Review data isolation.
- [ ] Review file upload security.
- [ ] Review payment callback security.
- [ ] Review environment variable handling.

Exit gate:

- [ ] Core workflows are tested and production risks are documented or resolved.

## Phase 14: Deployment

- [ ] Configure Heroku app.
- [ ] Configure Heroku PostgreSQL.
- [ ] Configure Cloudinary.
- [ ] Configure Redis for Celery.
- [ ] Configure M-Pesa credentials.
- [ ] Configure email provider.
- [ ] Configure production environment variables.
- [ ] Run migrations on Heroku.
- [ ] Collect static files.
- [ ] Start web dyno.
- [ ] Start worker dyno.
- [ ] Verify landing page.
- [ ] Verify tutor registration.
- [ ] Verify student login.
- [ ] Verify M-Pesa sandbox or live payment.
- [ ] Verify assessment publishing.
- [ ] Verify exam taking.
- [ ] Verify proctoring logs.

Exit gate:

- [ ] The platform runs correctly in production with web and worker processes.

## Phase 15: Launch Readiness

- [ ] Add privacy policy.
- [ ] Add terms of service.
- [ ] Add pricing page.
- [ ] Add help pages.
- [ ] Add tutor onboarding.
- [ ] Add student onboarding.
- [ ] Add admin operating guide.
- [ ] Add backup plan.
- [ ] Add monitoring/log review plan.
- [ ] Add support contact workflow.
- [ ] Perform final mobile QA.
- [ ] Perform final payment QA.
- [ ] Perform final security review.

Exit gate:

- [ ] The system is ready for real tutors, students, schools, and payments.

## Current Overall Status

- [~] Analysis and roadmap
- [x] Foundation
- [x] Accounts and roles
- [x] Landing page
- [x] Tutor workflows
- [ ] Student workflows
- [ ] Payments
- [ ] Exam engine
- [ ] Anti-cheating
- [ ] Reports
- [ ] Deployment
