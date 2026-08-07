FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=False

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

# No secrets needed at build time: SECRET_KEY/DATABASE_URL have safe fallbacks in settings.py,
# and collectstatic doesn't touch the database. DJANGO_DEBUG=False (set above) matters here: the
# staticfiles backend is manifest-based (whitenoise) only when DEBUG=False, and that's the backend
# this build must collect for -- Cloud Run running the resulting image also needs DEBUG=False, or
# it'll look for a manifest that was never built.
RUN python manage.py collectstatic --noinput

EXPOSE 8080

# Shell form (not exec-array) so $PORT is substituted -- Cloud Run injects it at runtime.
CMD gunicorn forkcast.wsgi:application --bind 0.0.0.0:${PORT:-8080}
