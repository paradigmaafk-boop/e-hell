FROM python:3.10-slim

WORKDIR /app

# Копируем все файлы
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir Flask pandas openpyxl Werkzeug gunicorn

# Создаем папку для базы данных и даем права на запись
RUN mkdir -p /app/data && chmod 777 /app/data

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD gunicorn app:app --bind 0.0.0.0:8000
