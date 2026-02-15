# --------------------------------------------------------------------------------
# Stage 1: Builder
# --------------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock /app/

# --frozen: requires uv.lock
# --no-install-project: installs only libraries (Django, etc)
RUN uv sync --frozen --no-install-project

# Copy the rest of the application
COPY . /app

# Sync again to ensure the project itself is "installed" if needed
RUN uv sync --frozen

# --------------------------------------------------------------------------------
# Stage 2: Final Runtime Image
# --------------------------------------------------------------------------------
FROM python:3.14-slim-bookworm

# 1. Install GeoDjango System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup non-root user
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

# 3. Copy from builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# 4. Set PATH
ENV PATH="/app/.venv/bin:$PATH"

# 5. Security & Run
USER nonroot
WORKDIR /app
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
