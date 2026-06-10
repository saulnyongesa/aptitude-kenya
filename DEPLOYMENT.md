# Aptitude Kenya Deployment

This guide prepares the project for Heroku with PostgreSQL, Redis/Celery, Cloudinary, email, and M-Pesa credentials.

## Heroku App

```powershell
heroku login
heroku create aptitude-kenya
heroku addons:create heroku-postgresql:essential-0 --app aptitude-kenya
heroku addons:create heroku-redis:mini --app aptitude-kenya
```

## Required Config Vars

```powershell
heroku config:set APP_ENV=production --app aptitude-kenya
heroku config:set DJANGO_SETTINGS_MODULE=config.settings.production --app aptitude-kenya
heroku config:set SECRET_KEY="<long-random-secret>" --app aptitude-kenya
heroku config:set ALLOWED_HOSTS="aptitude-kenya.herokuapp.com,aptitudekenya.ac.ke,portal.aptitudekenya.ac.ke" --app aptitude-kenya
heroku config:set CSRF_TRUSTED_ORIGINS="https://aptitude-kenya.herokuapp.com,https://aptitudekenya.ac.ke,https://portal.aptitudekenya.ac.ke" --app aptitude-kenya
heroku config:set BACKGROUND_TASK_BACKEND=celery --app aptitude-kenya
heroku config:set SECURE_SSL_REDIRECT=True --app aptitude-kenya
```

`DATABASE_URL` and `REDIS_URL` are provided by the Heroku add-ons.

## Cloudinary

```powershell
heroku config:set CLOUDINARY_CLOUD_NAME="<cloud-name>" --app aptitude-kenya
heroku config:set CLOUDINARY_API_KEY="<api-key>" --app aptitude-kenya
heroku config:set CLOUDINARY_API_SECRET="<api-secret>" --app aptitude-kenya
```

## Email

Set your provider's SMTP values. Example variable names:

```powershell
heroku config:set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend --app aptitude-kenya
heroku config:set EMAIL_HOST="<smtp-host>" --app aptitude-kenya
heroku config:set EMAIL_PORT=587 --app aptitude-kenya
heroku config:set EMAIL_USE_TLS=True --app aptitude-kenya
heroku config:set EMAIL_HOST_USER="<smtp-user>" --app aptitude-kenya
heroku config:set EMAIL_HOST_PASSWORD="<smtp-password>" --app aptitude-kenya
heroku config:set DEFAULT_FROM_EMAIL="Aptitude Kenya <no-reply@aptitudekenya.ac.ke>" --app aptitude-kenya
```

## M-Pesa

```powershell
heroku config:set MPESA_ENVIRONMENT=sandbox --app aptitude-kenya
heroku config:set MPESA_CONSUMER_KEY="<consumer-key>" --app aptitude-kenya
heroku config:set MPESA_CONSUMER_SECRET="<consumer-secret>" --app aptitude-kenya
heroku config:set MPESA_SHORTCODE="<shortcode>" --app aptitude-kenya
heroku config:set MPESA_PASSKEY="<passkey>" --app aptitude-kenya
heroku config:set MPESA_CALLBACK_BASE_URL="https://aptitude-kenya.herokuapp.com" --app aptitude-kenya
heroku config:set MPESA_CALLBACK_TOKEN="<optional-token>" --app aptitude-kenya
```

If `MPESA_CALLBACK_TOKEN` is set, the callback URL must include `?token=<optional-token>` or the callback proxy must send `X-MPESA-CALLBACK-TOKEN`.

## Deploy

```powershell
git push heroku main
heroku ps:scale web=1 worker=1 --app aptitude-kenya
heroku run python manage.py check --deploy --app aptitude-kenya
heroku run python manage.py createsuperuser --app aptitude-kenya
```

The `Procfile` release command runs migrations automatically on each deploy.

## Verification Checklist

- Open the landing page.
- Register a tutor.
- Log in through `/portal/`.
- Create a classroom and student.
- Create and publish an assessment.
- Confirm subscription or per-assessment billing flow.
- Run an M-Pesa sandbox payment once Daraja credentials are configured.
- Log in as a student and complete an assessment.
- Trigger a proctoring violation and confirm it is logged.
- Open the admin console and background jobs page.
- Confirm the worker dyno processes queued jobs.
