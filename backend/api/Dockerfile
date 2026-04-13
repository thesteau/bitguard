FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

COPY requirements.txt .

RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app

# Model artifacts are mounted into /app/pickle by the compose deployments.
RUN mkdir -p /app/pickle

EXPOSE 8444

CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8444"]
