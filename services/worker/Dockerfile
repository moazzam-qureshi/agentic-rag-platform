# syntax=docker/dockerfile:1.7

# === Builder ===
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# === Runtime ===
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    # Worker imports api.db.opensearch_store from inside the cleanup actor,
    # so both api and worker source trees must be on PYTHONPATH.
    PYTHONPATH="/app:/app/services/api/src:/app/services/worker/src"

# LibreOffice is required for DOCX/XLSX -> PDF before VLM page rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY pyproject.toml uv.lock ./
COPY shared /app/shared
COPY services/api /app/services/api
COPY services/worker /app/services/worker

# Default: run the Dramatiq worker. The scheduler service overrides this
# via `command:` in docker-compose.yml.
CMD ["dramatiq", "worker.main", "--processes", "1", "--threads", "2"]
