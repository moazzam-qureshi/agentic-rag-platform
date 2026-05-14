# syntax=docker/dockerfile:1.7

# === Builder ===
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Build deps for native wheels we don't always get prebuilt for slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv via the official installer (smaller than the full python image).
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
    PYTHONPATH="/app:/app/services/api/src"

# Runtime system deps: just curl for the healthcheck. PyMuPDF ships its
# own renderer; PDF rendering needs nothing else from apt.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

# Pre-fetch the sentence-transformers embedding model into the image so the
# first chat query doesn't pay a ~90MB HuggingFace download. The cache lives
# at /root/.cache/huggingface; SentenceTransformer reads from there on init.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Source layout: pyproject + workspace dirs.
COPY pyproject.toml uv.lock alembic.ini ./
COPY alembic /app/alembic
COPY shared /app/shared
COPY services/api /app/services/api

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
