FROM python:3.10-slim

WORKDIR /app

# Системные зависимости для psycopg2, pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

# 1 CPU → 1 воркер с 8 потоками gthread.
# --max-requests мягко перезапускает воркер каждые 500 запросов.
CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--worker-class", "gthread", \
     "--threads", "8", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--max-requests", "500", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
