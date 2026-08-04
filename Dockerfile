FROM python:3.10-slim

WORKDIR /app

COPY . /app

# Устанавливаем зависимости с фиксированными версиями
RUN pip install --no-cache-dir \
    Flask==3.1.3 \
    Werkzeug==3.1.8 \
    gunicorn==26.0.0 \
    pandas==2.0.3 \
    numpy==1.24.4 \
    openpyxl==3.1.2

# Даем права на запись
RUN chmod -R 777 /app

EXPOSE 8000

CMD gunicorn app:app --bind 0.0.0.0:8000
