# syntax=docker/dockerfile:1.7
# Istari — one image: FastAPI serves the API and the built SPA (same origin).
#
#   Stage 1  frontend  pnpm build  -> /web/dist
#   Stage 2  runtime   uv sync (no dev) + app code + dist as /app/static
#
# Runs as a non-root user, read-only root FS friendly (writes only to /tmp
# and the /backups volume). No secrets are baked in; everything comes from
# the environment at run time (see .env.example).

# ─── Stage 1: build the SPA ───────────────────────────────────────────
FROM node:26-slim AS frontend
# Build stamp shown in every page's footer (see backend/app/buildinfo.py).
ARG GIT_COMMIT=unknown
ENV PNPM_HOME=/pnpm PATH="/pnpm:$PATH" CI=true GIT_COMMIT=$GIT_COMMIT
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate
WORKDIR /web
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile
COPY frontend/ ./
COPY brand/ /brand/
COPY VERSION /VERSION
RUN pnpm run build

# ─── Stage 2: runtime ─────────────────────────────────────────────────
FROM python:3.13-slim AS runtime
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=
ARG APP_VERSION=dev
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /usr/local/bin/uv

# postgresql-client provides pg_dump / pg_restore for `make backup` / `make restore`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --shell /usr/sbin/nologin --create-home app \
    && mkdir -p /backups && chown app:app /backups

WORKDIR /app

# Dependencies first (cached unless the lockfile changes).
COPY --chown=app:app backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev --no-install-project

# Application, migrations, content packs, built SPA.
COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/alembic ./alembic
COPY --chown=app:app backend/alembic.ini ./alembic.ini
COPY --chown=app:app content/ /content/
COPY --chown=app:app scripts/backup.sh scripts/restore.sh ./scripts/
COPY --chown=app:app VERSION /VERSION
COPY --from=frontend --chown=app:app /web/dist ./static

ENV CONTENT_PACKS_DIR=/content/packs \
    BACKUP_DIR=/backups \
    STATIC_DIR=/app/static \
    BIND_HOST=0.0.0.0 \
    PORT=8000 \
    GIT_COMMIT=$GIT_COMMIT \
    BUILD_DATE=$BUILD_DATE

LABEL org.opencontainers.image.title="istari" \
      org.opencontainers.image.source="https://github.com/rex/istari" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$GIT_COMMIT" \
      org.opencontainers.image.created="$BUILD_DATE"

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health').read()" || exit 1

# Migrate, then serve. `alembic upgrade head` is idempotent.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host ${BIND_HOST} --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
