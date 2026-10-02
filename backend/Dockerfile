# HemaNet backend image: one image for the `api`, `worker` and `migrate` processes (ADR-001).
FROM docker.io/library/python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_APP=wsgi

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

WORKDIR /app

# Install locked runtime dependencies first for better layer caching.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app
COPY migrations ./migrations
COPY wsgi.py worker.py ./

# Run as an unprivileged user.
RUN useradd --system --uid 10001 --create-home hemanet
USER hemanet

EXPOSE 8000
# Request logging is done by the app (path only, redacted); gunicorn's access log
# would include query strings, so it is left off.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "wsgi:app"]
