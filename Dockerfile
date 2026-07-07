# Python ka official slim image
FROM python:3.12-slim

# System dependencies jo EasyOCR/OpenCV ke liye chahiye
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Requirements install karo
RUN pip install --no-cache-dir -r requirements.txt

# Render ka default port
EXPOSE 10000

# Server start command
# --worker-class gevent bahut kam RAM leta hai
CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:10000 --worker-class gevent --workers 1 --timeout 300