"""Application settings — loaded once from the environment (and `.env`)."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every variable the backend reads. Documented in `.env.example`."""

    model_config = SettingsConfigDict(
        # The backend runs from `backend/`; the repo-root `.env` is the shared one.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "istari"
    # Required on purpose: no default DSN, so a missing `.env` fails fast instead of
    # quietly pointing at a database with a well-known password.
    database_url: str
    # Isolated database for `make test` / `make e2e`. Defaults to `database_url` with
    # `_test` appended to the database name (same server, same credentials).
    test_database_url: str = ""

    bind_host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    session_cookie_name: str = "istari_session"
    session_cookie_secure: bool = False
    session_ttl_hours: int = Field(default=720, ge=1)

    login_max_attempts: int = Field(default=5, ge=1)
    login_window_seconds: int = Field(default=900, ge=1)
    login_lockout_seconds: int = Field(default=300, ge=1)

    timezone: str = "America/Chicago"
    content_packs_dir: str = "../content/packs"
    backup_dir: str = "../backups"
    # Built SPA directory. Served at `/` when it exists (production image).
    static_dir: str = "static"

    # Build stamp shown on every page. The image sets both (`make docker-build`);
    # in development the commit comes from the git checkout and the date stays unset.
    git_commit: str = ""
    build_date: str = ""

    # Watch: the mounted learning share and which topic folders under it hold courses.
    # Unset means the Watch area explains that nothing is configured. Read-only.
    learning_root: str = ""
    learning_topics: str = (
        "Cloud/AWS,Cloud/Terraform-IaC,Cloud/General-Certs,"
        "Kubernetes/CKA,Kubernetes/CKAD,Kubernetes/CKS,Kubernetes/Helm-GitOps"
    )

    @model_validator(mode="after")
    def default_test_database_url(self) -> Settings:
        if not self.test_database_url:
            parts = urlsplit(self.database_url)
            self.test_database_url = urlunsplit(parts._replace(path=f"{parts.path}_test"))
        return self


settings = Settings()
