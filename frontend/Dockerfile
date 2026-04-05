FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

COPY requirements.txt .

RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    RELOAD=false

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY templates ./templates
COPY static ./static

EXPOSE 8000

CMD sh -c "if [ \"$RELOAD\" = \"true\" ]; then uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; else uvicorn app.main:app --host 0.0.0.0 --port 8000; fi"
