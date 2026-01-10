# syntax=docker/dockerfile:1.6

ARG PANDOC_VERSION=3.8.3
ARG PANDOC_SHA256=d7fac78b58b8c8da39254955eff321233ab97d74e8b2d461c0f0719a1fb5f357
ARG PANDOC_SHA256_ARM64=566334d71769d15dfabf6514882ad6a41d57c0400ded1b6677bd72de7ec66a3d

# Stage 1: Build frontend assets (full SPA)
FROM node:22-slim AS frontend-builder

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy workspace config and SPA package
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./frontend/
COPY frontend/apps/skriptoteket/package.json ./frontend/apps/skriptoteket/

# Install dependencies from workspace root
WORKDIR /app/frontend
RUN --mount=type=cache,target=/pnpm/store,sharing=locked \
    pnpm install --frozen-lockfile --store-dir /pnpm/store

# Copy source and build
COPY frontend/apps/skriptoteket/ ./apps/skriptoteket/
# Copy design tokens from backend (needed for CSS import resolution)
COPY src/skriptoteket/web/static/css/huleedu-design-tokens.css /app/src/skriptoteket/web/static/css/huleedu-design-tokens.css
RUN pnpm --filter @skriptoteket/spa build


# Stage 2: Base system deps + Pandoc (shared)
FROM python:3.13-slim AS pandoc-base

ARG PANDOC_VERSION
ARG PANDOC_SHA256
ARG PANDOC_SHA256_ARM64
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDM_CHECK_UPDATE=false

WORKDIR /app

# System deps:
# - WeasyPrint: pango/cairo/gdk-pixbuf + shared-mime-info
# - Pandoc: used by pypandoc at runtime
# - Fonts: for PDF generation fidelity
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    patch \
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
    && case "$TARGETARCH" in \
        amd64|"") PANDOC_ARCH="amd64"; PANDOC_SHA="$PANDOC_SHA256" ;; \
        arm64) PANDOC_ARCH="arm64"; PANDOC_SHA="$PANDOC_SHA256_ARM64" ;; \
        *) echo "Unsupported TARGETARCH=$TARGETARCH" >&2; exit 1 ;; \
    esac \
    && PANDOC_DEB="pandoc-${PANDOC_VERSION}-1-${PANDOC_ARCH}.deb" \
    && curl -fsSL -o "/tmp/${PANDOC_DEB}" "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/${PANDOC_DEB}" \
    && echo "${PANDOC_SHA}  /tmp/${PANDOC_DEB}" | sha256sum -c - \
    && dpkg -i "/tmp/${PANDOC_DEB}" \
    && apt-get -y -f install \
    && rm -f "/tmp/${PANDOC_DEB}" \
    && rm -rf /var/lib/apt/lists/*


# Stage 3: Build Python dependencies
FROM pandoc-base AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDM_CHECK_UPDATE=false \
    PDM_CACHE_DIR=/root/.cache/pdm

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pdm==2.26.2

COPY pyproject.toml pdm.lock ./
RUN --mount=type=cache,target=/root/.cache/pdm,sharing=locked \
    pdm config python.use_venv false \
    && pdm install --frozen-lockfile --prod --no-editable --no-self


FROM pandoc-base AS production

ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDM_CHECK_UPDATE=false

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    jq \
    ripgrep \
    fd-find \
    bat \
    fzf \
    tree \
    && rm -rf /var/lib/apt/lists/*

# DevOps DX parity tools (see skriptoteket-devops skill/runbook)
RUN ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && ln -sf /usr/bin/batcat /usr/local/bin/bat \
    && YQ_ARCH="amd64" \
    && if [ "$TARGETARCH" = "arm64" ]; then YQ_ARCH="arm64"; fi \
    && curl -fsSL "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_${YQ_ARCH}" -o /usr/local/bin/yq \
    && chmod +x /usr/local/bin/yq

RUN pip install --no-cache-dir pdm==2.26.2

COPY --from=builder /app/__pypackages__ /app/__pypackages__
# SPA assets are built to ../../../src/skriptoteket/web/static/spa relative to frontend/apps/skriptoteket
COPY --from=frontend-builder /app/src/skriptoteket/web/static/spa ./src/skriptoteket/web/static/spa
COPY pyproject.toml pdm.lock ./
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src

EXPOSE 8000
CMD ["pdm", "run", "serve"]


FROM production AS development

RUN --mount=type=cache,target=/root/.cache/pdm,sharing=locked \
    pdm install --frozen-lockfile -G monorepo-tools -G dev --no-editable --no-self

CMD ["pdm", "run", "dev-docker"]
