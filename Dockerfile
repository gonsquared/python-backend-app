FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup --system appgroup && adduser --system --group appuser

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY .env_dev .env

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 4000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000"]
