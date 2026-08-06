FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

# No secrets needed at build time: SECRET_KEY/DATABASE_URL have safe fallbacks in settings.py,
# and collectstatic doesn't touch the database.
RUN python manage.py collectstatic --noinput

EXPOSE 8080

# Shell form (not exec-array) so $PORT is substituted -- Cloud Run injects it at runtime.
CMD gunicorn forkcast.wsgi:application --bind 0.0.0.0:${PORT:-8080}
