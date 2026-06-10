release: python manage.py migrate --noinput
web: gunicorn config.wsgi --log-file - --workers=${WEB_CONCURRENCY:-3}
worker: celery -A config worker --loglevel=info
