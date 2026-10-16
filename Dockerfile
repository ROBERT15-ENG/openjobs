FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN python scripts/apply_migrations.py || true

EXPOSE 5700

# P1: graceful shutdown via gunicorn (see gunicorn.conf.py)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "api.server:app"]
