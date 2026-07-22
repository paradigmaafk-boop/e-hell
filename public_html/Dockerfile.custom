FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

RUN groupadd --gid 2000 app && useradd --uid 2000 --gid 2000 -m -d /app app

COPY --chown=app:app . .

RUN pip install --no-cache-dir flask gunicorn

USER app

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
