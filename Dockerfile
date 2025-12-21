# syntax=docker/dockerfile:1

# Stage 1: Build frontend SPA assets
FROM node:22-slim AS frontend-builder

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy workspace config and lockfile
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./frontend/
COPY frontend/islands/package.json ./frontend/islands/

# Install dependencies from workspace root
WORKDIR /app/frontend
RUN pnpm install --frozen-lockfile

# Copy source and build
COPY frontend/islands/ ./islands/
RUN pnpm --filter @skriptoteket/islands build


# Stage 2: Build Python dependencies
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDM_CHECK_UPDATE=false

WORKDIR /app

# System deps:
# - WeasyPrint: pango/cairo/gdk-pixbuf + shared-mime-info
# - Pandoc: used by pypandoc at runtime
# - Fonts: for PDF generation fidelity
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pandoc \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    shared-mime-info \
    fontconfig \
    fonts-liberation2 \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pdm==2.26.2

COPY pyproject.toml pdm.lock ./
RUN pdm config python.use_venv false \
    && pdm install --frozen-lockfile --prod --no-editable --no-self


FROM python:3.13-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDM_CHECK_UPDATE=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    shared-mime-info \
    fontconfig \
    fonts-liberation2 \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pdm==2.26.2

COPY --from=builder /app/__pypackages__ /app/__pypackages__
# SPA assets are built to ../../src/skriptoteket/web/static/spa relative to frontend/islands
COPY --from=frontend-builder /app/src/skriptoteket/web/static/spa ./src/skriptoteket/web/static/spa
COPY pyproject.toml pdm.lock ./
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src

EXPOSE 8000
CMD ["pdm", "run", "serve"]


FROM production AS development

RUN pdm install --frozen-lockfile -G monorepo-tools -G dev --no-editable --no-self

CMD ["pdm", "run", "dev-docker"]
