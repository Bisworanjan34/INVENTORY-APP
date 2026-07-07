# Python ka official image use karo
FROM python:3.12-slim

# System dependencies jo EasyOCR ke liye chahiye
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Requirements install karo
RUN pip install --no-cache-dir -r requirements.txt

# Port 10000 (Render ka default)
EXPOSE 10000

# Server start command
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:10000"]