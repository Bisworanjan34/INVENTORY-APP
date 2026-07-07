# Python ka official slim image
FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Yahan PIP ko upgrade karein
RUN pip install --no-cache-dir --upgrade pip

# Ab requirements install karein
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000

CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:10000 --workers 3 --timeout 300