# Python ka official slim image (Lightweight)
FROM python:3.12-slim

# System dependencies (sirf zaroori cheezein)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Requirements install karo
RUN pip install --no-cache-dir -r requirements.txt

# Render ka default port
EXPOSE 10000

# Server start command
# Workers 2 ya 3 rakhein agar Render ka RAM plan allow kare
CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:10000 --workers 3 --timeout 300