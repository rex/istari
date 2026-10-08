# Deployment

Istari is a single-owner application: one PostgreSQL database and one container that
serves the API and the built SPA from the same origin. Nothing here assumes a hostname,
a reverse proxy product or a particular host; those decisions belong to whoever runs it.

## Local development

```bash
cp .env.example .env            # set POSTGRES_PASSWORD before the first db-up
make install                    # uv sync + pnpm install
make db-up                      # Postgres on 127.0.0.1:5433 (compose)
make db-migrate                 # alembic upgrade head
make seed                       # import content/packs/*/pack.json
make bootstrap-owner USERNAME=<you>   # prompts for the password; never a default
make dev                        # API on :8000, Vite on :5173
```

`make test` runs the backend suite against `<DATABASE_URL>_test` (created by the compose
init script) and the frontend unit tests. `make e2e` builds the SPA and runs Playwright
against the API serving it, using the test database.

## Container image

`Dockerfile` is a two-stage build: Node builds the SPA, then a `python:3.13-slim` runtime
with `uv` installs the backend, copies `content/` and the backup scripts, and serves
`frontend/dist` as static files. The process runs as uid 10001, the compose service drops
all capabilities, mounts the root file system read-only and uses `tmpfs` for `/tmp`.
The container command runs `alembic upgrade head` before starting uvicorn, so a new image
migrates on start.

`make docker-build` and `make docker-up` pass `APP_VERSION`, `GIT_COMMIT` and
`BUILD_DATE` as build args. The image carries them as OCI labels and environment
variables, `/api/health` reports them together with the process start time, and the
footer of every page (the login page included) shows version, commit, build time and
"up since". The SPA bundle also embeds the commit it was built from: when it differs from
the API's, the footer says so and asks for a reload, which is what a stale cached bundle
after a deploy looks like.

```bash
make docker-build
make docker-up        # app on 127.0.0.1:8000, db on 127.0.0.1:5433
```

Both ports bind to loopback only. Put a TLS-terminating reverse proxy in front for anything
beyond the machine itself, set `SESSION_COOKIE_SECURE=true`, and keep the database port
unpublished. The app does not do its own TLS.

## Configuration

Every variable is documented in `.env.example`. The ones that matter in production:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | asyncpg DSN; required, no default |
| `POSTGRES_PASSWORD` | compose db password; the DSN interpolates it |
| `SESSION_COOKIE_SECURE` | `true` behind HTTPS |
| `SESSION_TTL_HOURS` | idle session lifetime (default 720) |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` / `LOGIN_LOCKOUT_SECONDS` | login throttle |
| `TIMEZONE` | display timezone (storage is UTC); default `America/Chicago` |
| `LOG_LEVEL` | structured JSON logs; every line carries a request id |
| `GIT_COMMIT` / `BUILD_DATE` | build stamp; set by the image, not by `.env` |
| `LEARNING_ROOT` / `LEARNING_TOPICS` | the mounted learning share and its course folders for Watch; unset disables Watch |

Watch reads the share in place. On the Mac the SMB share is already mounted under
`/Volumes`; in a container the share must be mounted read-only into the container at
the path `LEARNING_ROOT` names. Video is streamed by the API with Range support, so the
container needs read access to the files and nothing else; nothing is ever written to
the share.

The owner account is created with the CLI (`bootstrap-owner`); there is no default
password and no sign-up. `--reset-password` rotates it.

## Health and logs

`GET /api/health` returns service name, version and database reachability; the compose
healthcheck and any proxy probe should use it. Logs go to stdout as JSON with
`request_id`, method, path, status and duration; the same id is returned in the
`X-Request-ID` response header.

## Backups

```bash
make backup                                   # pg_dump -Fc into BACKUP_DIR, mode 600
make restore FILE=backups/<dump> TARGET_DB=istari_restore   # into an isolated database
```

Restore defaults to a separate database so a bad dump never overwrites live data; the
integration test `test_backup_restore.py` exercises the round trip into
`istari_restore_test`. Dumps contain learning history and the owner's password hash: treat
them as secrets (the `backups/` directory is git-ignored).

## Upgrades

Pull, `make docker-build`, `make docker-up`. Migrations run on container start. Content
updates are `make seed` (idempotent; see `docs/content-schema.md`).

## Homelab note

Deploying to Pierce's homelab is done through the lab's own prescribed workflows (Arda,
the inventory and Flux repositories), not from this repository. This document deliberately
names no hosts, DNS names or proxy configuration; the image and compose file above are the
whole interface.
