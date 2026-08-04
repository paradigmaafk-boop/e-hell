FROM python:3.10-slim

WORKDIR /app

# Копируем все файлы проекта
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir Flask pandas openpyxl Werkzeug gunicorn

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD gunicorn app:app --bind 0.0.0.0:8000
