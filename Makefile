# ╔══════════════════════════════════════════════════════════════════════╗
# ║          istari — Makefile                                           ║
# ║          FastAPI + PostgreSQL (backend/) · React/Vite (frontend/)   ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# Usage: make <target>
# Run `make help` for a full list of available targets.

.PHONY: help help-stack install env env-check setup validate update info \
        dev dev-api dev-web build start lint typecheck check-architecture check-docs \
        check-precommit check-skeleton sync-skeleton check-skills stamp-skill fix test \
        test-backend test-frontend e2e \
        bump-patch bump-minor bump-major check-version-bumped version \
        clean clean-all \
        docker-build docker-up docker-down docker-logs docker-run docker-stop docker-clean \
        db-up db-down db-migrate db-revision db-reset seed bootstrap-owner \
        backup restore secrets-scan \
        check-if-the-agent-can-consider-this-task-completed

# ─── Configuration ────────────────────────────────────────────────────
# Prefer Homebrew zsh on macOS, then any zsh on PATH, then /bin/bash as
# a CI-runner fallback (most CI runners don't ship zsh by default;
# without this third fallback SHELL resolves to '' and `make: -c: No
# such file or directory` fires on the first recipe). Keep recipes
# POSIX-compatible — no `[[ ]]`, no `${var//foo/bar}` substitution, no
# zsh globbing — so /bin/bash works as a true fallback.
SHELL       := $(or $(wildcard /opt/homebrew/bin/zsh),$(shell command -v zsh),/bin/bash)
APP_NAME    ?= istari
PORT        ?= 8000
WEB_PORT    ?= 5173
NODE_ENV    ?= development
DOCKER_IMAGE := $(APP_NAME):latest
BACKEND     := backend
FRONTEND    := frontend
UV          := cd $(BACKEND) && uv run
PNPM        := cd $(FRONTEND) && pnpm
BACKUP_DIR  ?= backups

# Colors for output
CYAN   := $(shell printf '\033[36m')
GREEN  := $(shell printf '\033[32m')
YELLOW := $(shell printf '\033[33m')
RED    := $(shell printf '\033[31m')
RESET  := $(shell printf '\033[0m')
BOLD   := $(shell printf '\033[1m')

# ─── Help ─────────────────────────────────────────────────────────────

## help: Display this help message with all available targets
help:
	@echo ""
	@echo "$(BOLD)$(CYAN)$(APP_NAME)$(RESET)"
	@echo "$(CYAN)════════════════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(BOLD)Setup & Installation$(RESET)"
	@echo "  $(GREEN)make install$(RESET)              Install dependencies"
	@echo "  $(GREEN)make env$(RESET)                  Create .env from template"
	@echo "  $(GREEN)make env-check$(RESET)            Verify required env vars"
	@echo "  $(GREEN)make setup$(RESET)                Full setup: install + env + typecheck"
	@echo ""
	@echo "$(BOLD)Development$(RESET)"
	@echo "  $(GREEN)make dev$(RESET)                  API (127.0.0.1:$(PORT)) + Vite (127.0.0.1:$(WEB_PORT)) with reload"
	@echo "  $(GREEN)make dev-api$(RESET)              API only"
	@echo "  $(GREEN)make dev-web$(RESET)              Vite only (proxies /api to the API)"
	@echo "  $(GREEN)make build$(RESET)                Build the SPA into backend/static"
	@echo "  $(GREEN)make start$(RESET)                Serve API + built SPA on one origin"
	@echo "  $(GREEN)make lint$(RESET)                 ruff + import-linter + eslint + prettier"
	@echo "  $(GREEN)make typecheck$(RESET)            mypy --strict + tsc"
	@echo "  $(GREEN)make check-architecture$(RESET)   Run repo-native architecture checks"
	@echo "  $(GREEN)make fix$(RESET)                  Auto-fix lint + format"
	@echo "  $(GREEN)make test$(RESET)                 pytest (needs db-up) + vitest"
	@echo "  $(GREEN)make e2e$(RESET)                  Playwright end-to-end (builds + starts the app)"
	@echo "  $(GREEN)make validate$(RESET)             Run aggregate validation: lint + typecheck + architecture + version-gate"
	@echo ""
	@echo "$(BOLD)Database & content$(RESET)"
	@echo "  $(GREEN)make db-up$(RESET)                Start PostgreSQL (compose, loopback:5433)"
	@echo "  $(GREEN)make db-down$(RESET)              Stop PostgreSQL (data volume kept)"
	@echo "  $(GREEN)make db-migrate$(RESET)           alembic upgrade head"
	@echo "  $(GREEN)make db-revision$(RESET)          New migration: MSG=\"describe change\" (autogenerate, then REVIEW)"
	@echo "  $(GREEN)make db-reset$(RESET)             Drop + recreate the dev database (destructive!)"
	@echo "  $(GREEN)make seed$(RESET)                 Import every content pack (idempotent)"
	@echo "  $(GREEN)make bootstrap-owner$(RESET)      Create the owner login: USERNAME=<name>"
	@echo ""
	@echo "$(BOLD)Backup & security$(RESET)"
	@echo "  $(GREEN)make backup$(RESET)               pg_dump -> $(BACKUP_DIR)/istari-<timestamp>.dump"
	@echo "  $(GREEN)make restore$(RESET)              Restore FILE=<dump> into DB=<name> (default: istari_restore)"
	@echo "  $(GREEN)make secrets-scan$(RESET)         gitleaks over history + working tree"
	@echo "  $(GREEN)make check-skills$(RESET)         Advisory: applied-skill provenance + drift (never fails)"
	@echo "  $(GREEN)make stamp-skill$(RESET)          Record an applied skill: SKILL=<id> [VERSION=x.y.z]"
	@echo ""
	@echo "$(BOLD)Versioning (required before every commit)$(RESET)"
	@echo "  $(GREEN)make version$(RESET)              Print current VERSION"
	@echo "  $(GREEN)make bump-patch$(RESET)           Bump patch (x.y.Z+1) — bug fixes / doc / refactor"
	@echo "  $(GREEN)make bump-minor$(RESET)           Bump minor (x.Y+1.0) — additive feature, backward-compat"
	@echo "  $(GREEN)make bump-major$(RESET)           Bump major (X+1.0.0) — breaking change"
	@echo ""
	@echo "$(BOLD)Docker$(RESET)"
	@echo "  $(GREEN)make docker-build$(RESET)         Build the image (SPA + API)"
	@echo "  $(GREEN)make docker-up$(RESET)            compose up: app + db on 127.0.0.1:$(PORT)"
	@echo "  $(GREEN)make docker-down$(RESET)          compose down (volumes kept)"
	@echo "  $(GREEN)make docker-logs$(RESET)          Follow app logs"
	@echo "  $(GREEN)make docker-clean$(RESET)         Remove image and containers"
	@echo ""
	@echo "$(BOLD)Maintenance$(RESET)"
	@echo "  $(GREEN)make clean$(RESET)                Remove build cache"
	@echo "  $(GREEN)make clean-all$(RESET)            Remove build cache + deps (destructive!)"
	@echo "  $(GREEN)make update$(RESET)               Update dependencies"
	@echo "  $(GREEN)make info$(RESET)                 Show project info"
	@echo ""
	@echo "$(BOLD)Completion$(RESET)"
	@echo "  $(GREEN)make check-if-the-agent-can-consider-this-task-completed$(RESET)"
	@echo "    Final verification gate (required before declaring a task complete)"
	@echo ""
	@echo "$(BOLD)Variables$(RESET)"
	@echo "  PORT=$(PORT)  (override: make dev PORT=3000)"
	@echo ""

# ─── Setup & Installation ────────────────────────────────────────────

## install: Install dependencies (uv venv on Python 3.13 + pnpm, both from lockfiles)
install:
	@echo "$(CYAN)Installing backend dependencies (uv)...$(RESET)"
	@cd $(BACKEND) && uv venv --python 3.13 --allow-existing .venv >/dev/null && uv sync --frozen --group dev
	@echo "$(CYAN)Installing frontend dependencies (pnpm)...$(RESET)"
	@$(PNPM) install --frozen-lockfile
	@echo "$(GREEN)Done.$(RESET)"

## env: Create .env from template if missing
env:
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			echo "$(YELLOW)Creating .env from .env.example...$(RESET)"; \
			cp .env.example .env; \
			echo "$(GREEN).env created. Configure before running.$(RESET)"; \
		else \
			echo "$(RED)No .env.example to copy from.$(RESET)"; exit 1; \
		fi \
	else \
		echo "$(YELLOW).env already exists, skipping.$(RESET)"; \
	fi

## env-check: Verify required env vars are set
env-check:
	@if [ ! -f .env ]; then echo "$(RED).env missing — run 'make env'.$(RESET)"; exit 1; fi
	@echo "$(GREEN).env present.$(RESET)"

## setup: Full project setup — deps, .env, database, migrations, content, owner
setup: install env db-up db-migrate seed typecheck
	@echo ""
	@echo "$(GREEN)$(BOLD)Setup complete!$(RESET)"
	@echo "  1. $(CYAN)make bootstrap-owner USERNAME=<you>$(RESET)   (prompts for a password)"
	@echo "  2. $(CYAN)make dev$(RESET)  then open http://127.0.0.1:$(WEB_PORT)"

## validate: Run the repo's aggregate validation flow
validate: lint typecheck check-architecture check-version-bumped check-skills
	@echo "$(GREEN)Validation complete.$(RESET)"

# ─── Versioning (non-negotiable: every commit gets a bump) ───────────

## bump-patch: Increment patch (x.y.Z+1) — bug fixes, docs, non-behavior changes
bump-patch:
	@scripts/bump_version.py patch

## bump-minor: Increment minor (x.Y+1.0) — additive features, backward-compatible
bump-minor:
	@scripts/bump_version.py minor

## bump-major: Increment major (X+1.0.0) — breaking change, removal, incompat behavior
bump-major:
	@scripts/bump_version.py major

## check-version-bumped: Fail if VERSION == HEAD's VERSION or CHANGELOG lacks matching entry
check-version-bumped:
	@if [ ! -f scripts/check_version_bumped.py ]; then \
		echo "$(RED)scripts/check_version_bumped.py is MISSING — the version$(RESET)"; \
		echo "$(RED)gate cannot run. Hard failure, never a skip — restore it via$(RESET)"; \
		echo "$(RED)re-run the agentic-skeleton bootstrap to restore it.$(RESET)"; \
		exit 1; \
	fi
	@python3 scripts/check_version_bumped.py

## version: Print current VERSION
version:
	@cat VERSION 2>/dev/null || echo "0.1.0 (VERSION file missing)"

# ─── Development ──────────────────────────────────────────────────────

## dev: API with reload + Vite dev server, both on loopback
dev:
	@echo "$(CYAN)API on http://127.0.0.1:$(PORT)  ·  web on http://127.0.0.1:$(WEB_PORT)$(RESET)"
	@trap 'kill 0' INT TERM; \
	( $(UV) uvicorn app.main:app --host 127.0.0.1 --port $(PORT) --reload ) & \
	( $(PNPM) run dev --host 127.0.0.1 --port $(WEB_PORT) ) & \
	wait

## dev-api: API only (uvicorn --reload on 127.0.0.1:PORT)
dev-api:
	@$(UV) uvicorn app.main:app --host 127.0.0.1 --port $(PORT) --reload

## dev-web: Vite only (proxies /api to 127.0.0.1:PORT)
dev-web:
	@$(PNPM) run dev --host 127.0.0.1 --port $(WEB_PORT)

## build: Typecheck + build the SPA, then stage it as backend/static for same-origin serving
build:
	@echo "$(CYAN)Building the SPA...$(RESET)"
	@$(PNPM) run build
	@rm -rf $(BACKEND)/static && cp -R $(FRONTEND)/dist $(BACKEND)/static
	@echo "$(GREEN)Built -> $(BACKEND)/static$(RESET)"

## start: Serve the API and the built SPA from one origin (loopback)
start:
	@test -f $(BACKEND)/static/index.html || { echo "$(RED)No build; run 'make build' first.$(RESET)"; exit 1; }
	@$(UV) uvicorn app.main:app --host 127.0.0.1 --port $(PORT)

## lint: ruff check + ruff format --check + import-linter; eslint + prettier --check
lint:
	@echo "$(CYAN)Linting backend...$(RESET)"
	@cd $(BACKEND) && uv run ruff check app tests && uv run ruff format --check app tests && uv run lint-imports
	@echo "$(CYAN)Linting frontend...$(RESET)"
	@$(PNPM) run lint
	@echo "$(GREEN)Lint clean.$(RESET)"

## typecheck: mypy --strict (backend) + tsc --noEmit (frontend)
typecheck:
	@echo "$(CYAN)Typechecking backend (mypy)...$(RESET)"
	@$(UV) mypy app tests
	@echo "$(CYAN)Typechecking frontend (tsc)...$(RESET)"
	@$(PNPM) run typecheck
	@echo "$(GREEN)Types clean.$(RESET)"

## check-architecture: Enforce VIBE.yaml line limits + module shape (fails closed)
check-architecture:
	@echo "$(CYAN)Checking architecture (line limits + module shape)...$(RESET)"
	@for s in check_architecture.py check_module_rules.py; do \
		if [ ! -f "scripts/$$s" ]; then \
			echo "$(RED)  scripts/$$s is MISSING — the architecture gate$(RESET)"; \
			echo "$(RED)  cannot run. Hard failure, never a skip. Restore it:$(RESET)"; \
			echo "$(RED)  re-run the agentic-skeleton bootstrap.$(RESET)"; \
			exit 1; \
		fi; \
	done
	@if command -v uv >/dev/null 2>&1; then \
		uv run scripts/check_architecture.py && uv run scripts/check_module_rules.py; \
	elif python3 -c 'import yaml' >/dev/null 2>&1; then \
		python3 scripts/check_architecture.py && python3 scripts/check_module_rules.py; \
	else \
		echo "$(RED)  Architecture gate cannot run: no 'uv', and no$(RESET)"; \
		echo "$(RED)  python3 with PyYAML. Install uv: https://docs.astral.sh/uv/$(RESET)"; \
		exit 1; \
	fi

## fix: Auto-fix lint issues and format everything
fix:
	@echo "$(CYAN)Auto-fixing...$(RESET)"
	@cd $(BACKEND) && uv run ruff check --fix app tests && uv run ruff format app tests
	@cd $(FRONTEND) && pnpm run format && pnpm exec eslint . --fix
	@echo "$(GREEN)Done.$(RESET)"

## test: Backend (pytest, needs `make db-up`) + frontend (vitest) — VIBE tests.mode=required
test: test-backend test-frontend
	@echo "$(GREEN)All test suites passed.$(RESET)"

## test-backend: pytest against TEST_DATABASE_URL (migrated by Alembic, truncated per test)
test-backend:
	@echo "$(CYAN)Backend tests (pytest)...$(RESET)"
	@$(UV) pytest -q

## test-frontend: vitest
test-frontend:
	@echo "$(CYAN)Frontend tests (vitest)...$(RESET)"
	@$(PNPM) run test

## e2e: Playwright against a built app on 127.0.0.1:$(PORT) (see frontend/playwright.config.ts)
e2e: build
	@echo "$(CYAN)End-to-end tests (Playwright)...$(RESET)"
	@export E2E_DATABASE_URL="$$($(UV) python -c 'from app.config import settings; print(settings.test_database_url)')" && \
		$(PNPM) run test:e2e

# ─── Docker ───────────────────────────────────────────────────────────

## docker-build: Build Docker image with version metadata
docker-build:
	@echo "$(CYAN)Building Docker image $(DOCKER_IMAGE)...$(RESET)"
	docker build \
		--build-arg APP_VERSION=$$(cat VERSION) \
		--build-arg GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
		--build-arg BUILD_DATE=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
		-t $(DOCKER_IMAGE) .

## docker-up: Build and start app + db via Compose (loopback only)
docker-up:
	@APP_VERSION=$$(cat VERSION) \
	GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
	BUILD_DATE=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
	docker compose up -d --build --wait
	@echo "$(GREEN)Istari is up on http://127.0.0.1:$(PORT)$(RESET)"
	@echo "  First run: $(CYAN)docker compose exec -e ISTARI_OWNER_PASSWORD app python -m app.cli bootstrap-owner --username <you>$(RESET)"
	@echo "  Content:   $(CYAN)docker compose exec app python -m app.cli seed$(RESET)"

## docker-down: Stop the Compose stack (volumes kept)
docker-down:
	@docker compose down

## docker-logs: Follow application logs (JSON lines)
docker-logs:
	@docker compose logs -f app

## docker-run: Alias for docker-up
docker-run: docker-up

## docker-stop: Alias for docker-down
docker-stop: docker-down

## docker-clean: Remove containers and the image (volumes kept — use `docker compose down -v` to drop data)
docker-clean: docker-down
	@docker rmi -f $(DOCKER_IMAGE) 2>/dev/null || true
	@echo "$(GREEN)Image removed.$(RESET)"

# ─── Database & content ───────────────────────────────────────────────

## db-up: Start PostgreSQL via Compose and wait for healthy
db-up:
	@docker compose up -d --wait db
	@echo "$(GREEN)PostgreSQL ready on 127.0.0.1:$${POSTGRES_PORT:-5433} (databases: istari, istari_test)$(RESET)"

## db-down: Stop PostgreSQL (data volume kept)
db-down:
	@docker compose stop db

## db-migrate: Apply migrations (alembic upgrade head)
db-migrate:
	@$(UV) alembic upgrade head

## db-revision: Autogenerate a migration — MSG="..." — then REVIEW it before committing
db-revision:
	@if [ -z "$(MSG)" ]; then echo "$(RED)Usage: make db-revision MSG=\"describe change\"$(RESET)"; exit 1; fi
	@$(UV) alembic revision --autogenerate -m "$(MSG)" $(if $(REV_ID),--rev-id "$(REV_ID)",)
	@echo "$(YELLOW)Review backend/alembic/versions/ before committing.$(RESET)"

## db-reset: Drop and recreate the dev database, then migrate + seed (destructive — asks first)
db-reset:
	@echo "$(RED)This DROPS the dev database 'istari' (learning history included).$(RESET)"
	@read -p "Type 'reset' to continue: " confirm; \
	if [ "$$confirm" = "reset" ]; then \
		docker compose exec -T db psql -U istari -d postgres -c "DROP DATABASE IF EXISTS istari WITH (FORCE);" -c "CREATE DATABASE istari OWNER istari;"; \
		$(MAKE) db-migrate seed; \
	else echo "$(YELLOW)Cancelled.$(RESET)"; fi

## seed: Import every content pack under content/packs (idempotent; never touches notes or history)
seed:
	@$(UV) python -m app.cli seed

## corpus-ingest: Course directory -> private Markdown corpus — SRC="<dir>" [ALL=1 for a topic folder] [OUT=corpus]
corpus-ingest:
	@if [ -z "$(SRC)" ]; then echo "$(RED)Usage: make corpus-ingest SRC=\"<course dir>\" [ALL=1] [OUT=corpus]$(RESET)"; exit 1; fi
	@$(UV) python -m app.cli corpus-ingest "$(SRC)" $(if $(ALL),--all,) --out "$(abspath $(or $(OUT),corpus))"

## corpus-udemy: Udemy quiz HTML / results PDFs -> private pack — INPUTS="<files>" EXAM=SOA-C02 SLUG=<slug> NAME="<name>"
corpus-udemy:
	@if [ -z "$(INPUTS)" ] || [ -z "$(EXAM)" ] || [ -z "$(SLUG)" ] || [ -z "$(NAME)" ]; then \
		echo "$(RED)Usage: make corpus-udemy INPUTS=\"<files>\" EXAM=SOA-C02 SLUG=<slug> NAME=\"<name>\"$(RESET)"; exit 1; fi
	@$(UV) python -m app.cli corpus-udemy $(INPUTS) --exam "$(EXAM)" --slug "$(SLUG)" --name "$(NAME)" \
		--out "$(abspath content/private/$(SLUG).json)"

## bootstrap-owner: Create the single owner account — USERNAME=<name> (prompts for password)
bootstrap-owner:
	@if [ -z "$(USERNAME)" ]; then echo "$(RED)Usage: make bootstrap-owner USERNAME=<name>$(RESET)"; exit 1; fi
	@$(UV) python -m app.cli bootstrap-owner --username "$(USERNAME)"

# ─── Backup & security ────────────────────────────────────────────────

## backup: pg_dump (custom format) of DATABASE_URL into $(BACKUP_DIR)
backup:
	@BACKUP_DIR="$(BACKUP_DIR)" scripts/backup.sh

## restore: Restore FILE=<dump> into DB=<name> (default istari_restore; never the live db without DB=istari)
restore:
	@if [ -z "$(FILE)" ]; then echo "$(RED)Usage: make restore FILE=backups/<dump> [DB=istari_restore]$(RESET)"; exit 1; fi
	@TARGET_DB="$(or $(DB),istari_restore)" scripts/restore.sh "$(FILE)"

## secrets-scan: gitleaks over git history and the working tree (same rules as pre-commit + CI)
secrets-scan:
	@gitleaks git --no-banner --redact --config .gitleaks.toml . && gitleaks dir --no-banner --redact --config .gitleaks.toml .

# ─── Maintenance ──────────────────────────────────────────────────────

## clean: Remove build cache
clean:
	@echo "$(CYAN)Cleaning build cache...$(RESET)"
	@rm -rf $(FRONTEND)/dist $(BACKEND)/static $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
	@find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean.$(RESET)"

## clean-all: Remove build cache + dependencies (destructive — requires confirmation)
clean-all:
	@echo "$(YELLOW)WARNING: This will remove all dependencies and build artifacts.$(RESET)"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		rm -rf $(FRONTEND)/dist $(FRONTEND)/node_modules $(BACKEND)/static $(BACKEND)/.venv \
			$(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache; \
		echo "$(GREEN)Deep clean complete (lockfiles kept).$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi

## update: Update dependencies within pyproject/package.json ranges (review lockfile diffs)
update:
	@echo "$(CYAN)Updating dependencies...$(RESET)"
	@cd $(BACKEND) && uv lock --upgrade && uv sync --group dev
	@$(PNPM) update
	@echo "$(GREEN)Lockfiles updated — run 'make validate test'.$(RESET)"

## info: Show project state
info:
	@echo "$(BOLD)$(CYAN)Project Info$(RESET)"
	@echo "──────────────────────────────"
	@echo "  Project: $(APP_NAME)"
	@echo "  Branch:  $$(git branch --show-current 2>/dev/null || echo 'N/A')"
	@echo "  Commit:  $$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
	@echo "  Tree:    $$(git status --porcelain | wc -l | tr -d ' ') uncommitted changes"
	@echo "  Port:    $(PORT)"

# ─── Required-files + commit-surface gates ──────────────────────────

## check-docs: Enforce VIBE.yaml docs.*_required (fails closed)
check-docs:
	@echo "$(CYAN)Checking required collaboration files (VIBE.yaml docs)...$(RESET)"
	@if [ ! -f scripts/check_docs.py ]; then \
		echo "$(RED)  scripts/check_docs.py is MISSING — the docs gate$(RESET)"; \
		echo "$(RED)  cannot run. Hard failure. Re-run the bootstrap.$(RESET)"; \
		exit 1; \
	fi
	@if command -v uv >/dev/null 2>&1; then \
		uv run scripts/check_docs.py; \
	elif python3 -c 'import yaml' >/dev/null 2>&1; then \
		python3 scripts/check_docs.py; \
	else \
		echo "$(RED)  docs gate cannot run: no 'uv', no python3 + PyYAML.$(RESET)"; \
		exit 1; \
	fi

## check-precommit: Verify the pre-commit hook is installed (fails closed)
check-precommit:
	@echo "$(CYAN)Checking the pre-commit enforcement surface...$(RESET)"
	@if [ ! -f .pre-commit-config.yaml ]; then \
		echo "$(RED)  .pre-commit-config.yaml is MISSING — the commit-time$(RESET)"; \
		echo "$(RED)  enforcement surface is absent. Re-run the bootstrap.$(RESET)"; \
		exit 1; \
	fi
	@if ! command -v pre-commit >/dev/null 2>&1; then \
		echo "$(RED)  pre-commit is not installed — it is MANDATORY, not$(RESET)"; \
		echo "$(RED)  optional. Install it: uv tool install pre-commit$(RESET)"; \
		exit 1; \
	fi
	@HOOK=$$(git rev-parse --git-path hooks/pre-commit 2>/dev/null); \
	if [ -z "$$HOOK" ] || [ ! -f "$$HOOK" ] || ! grep -q pre-commit "$$HOOK" 2>/dev/null; then \
		echo "$(RED)  the pre-commit git hook is NOT installed. Run:$(RESET)"; \
		echo "$(RED)    pre-commit install$(RESET)"; \
		echo "$(RED)  A .pre-commit-config.yaml with no installed hook$(RESET)"; \
		echo "$(RED)  enforces nothing — fail closed.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)  pre-commit hook installed.$(RESET)"

## check-skeleton: Report drift vs the installed agentic-skeleton
check-skeleton:
	@echo "$(CYAN)Checking skeleton-owned files for drift...$(RESET)"
	@if [ ! -f scripts/sync_skeleton.py ]; then \
		echo "$(RED)  scripts/sync_skeleton.py is MISSING — cannot check$(RESET)"; \
		echo "$(RED)  skeleton drift. Re-run the agentic-skeleton bootstrap.$(RESET)"; \
		exit 1; \
	fi
	@if command -v uv >/dev/null 2>&1; then \
		uv run scripts/sync_skeleton.py --check; \
	else \
		python3 scripts/sync_skeleton.py --check; \
	fi

## sync-skeleton: Pull current skeleton-owned files into this repo
sync-skeleton:
	@if [ ! -f scripts/sync_skeleton.py ]; then \
		echo "$(RED)  scripts/sync_skeleton.py is MISSING.$(RESET)"; \
		exit 1; \
	fi
	@if command -v uv >/dev/null 2>&1; then \
		uv run scripts/sync_skeleton.py --apply; \
	else \
		python3 scripts/sync_skeleton.py --apply; \
	fi

## check-skills: Advisory applied-skill provenance + drift report (never fails validate)
check-skills:
	@echo "$(CYAN)Checking applied-skill provenance...$(RESET)"
	@if [ ! -f scripts/check_skills.py ]; then \
		echo "$(YELLOW)  scripts/check_skills.py not present — run 'make sync-skeleton'.$(RESET)"; \
	elif command -v uv >/dev/null 2>&1; then \
		uv run scripts/check_skills.py || true; \
	else \
		python3 scripts/check_skills.py || true; \
	fi

## stamp-skill: Record that a skill was applied (SKILL=<id> [VERSION=x.y.z])
stamp-skill:
	@if [ -z "$(SKILL)" ]; then \
		echo "$(RED)Usage: make stamp-skill SKILL=<id> [VERSION=x.y.z]$(RESET)"; exit 1; \
	fi
	@if [ ! -f scripts/stamp_skill.py ]; then \
		echo "$(RED)  scripts/stamp_skill.py missing — run 'make sync-skeleton'.$(RESET)"; exit 1; \
	fi
	@if command -v uv >/dev/null 2>&1; then \
		uv run scripts/stamp_skill.py "$(SKILL)" $(if $(VERSION),--version "$(VERSION)"); \
	else \
		python3 scripts/stamp_skill.py "$(SKILL)" $(if $(VERSION),--version "$(VERSION)"); \
	fi

# ─── Completion Gate ──────────────────────────────────────────────────

## check-if-the-agent-can-consider-this-task-completed: Final verification gate
check-if-the-agent-can-consider-this-task-completed: validate check-docs check-precommit test

## help-stack: Show which lang-* skill should fill in stub targets
help-stack:
	@echo "$(BOLD)$(CYAN)Stub targets and their owning lang-* skills$(RESET)"
	@echo ""
	@echo "Greenfield Makefile targets that print '(stub — overlay a lang-* skill"
	@echo "to fill this in)' need a stack-specific skill to overlay recipe bodies."
	@echo "Pick the skill matching VIBE.yaml::project.stack:"
	@echo ""
	@echo "  $(GREEN)Python / FastAPI$(RESET)        → invoke $(BOLD)/lang-python$(RESET)"
	@echo "  $(GREEN)Next.js / App Router$(RESET)    → invoke $(BOLD)/lang-react$(RESET)"
	@echo "  $(GREEN)Vite SPA$(RESET)                → invoke $(BOLD)/lang-react-spa$(RESET) + $(BOLD)/tool-vite$(RESET)"
	@echo "  $(GREEN)Go$(RESET)                      → invoke $(BOLD)/lang-go$(RESET) (when shipped)"
	@echo "  $(GREEN)MCP server$(RESET)              → invoke $(BOLD)/lang-mcp$(RESET) (when shipped)"
	@echo ""
	@echo "Each lang-* skill provides recipe bodies for: install / dev / build /"
	@echo "start / lint / typecheck / fix / test / update."
	@echo ""
	@echo "Until a lang-* overlay is applied, the stubs do nothing — that is by"
	@echo "design (the skeleton stays stack-agnostic). See"
	@echo "agentic-skeleton/SKILL.md for skill composition guidance."
	@echo ""
	@echo "$(BOLD)$(GREEN)✓ All gates passed. Task may be declared complete.$(RESET)"
	@echo ""
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(YELLOW)NOTE: working tree is dirty:$(RESET)"; \
		git status --short; \
		echo ""; \
		echo "$(YELLOW)The gates passed, but VIBE.yaml clean_worktree_required_on_completion$(RESET)"; \
		echo "$(YELLOW)may still apply. Commit or stash before declaring done.$(RESET)"; \
	fi

.DEFAULT_GOAL := help
