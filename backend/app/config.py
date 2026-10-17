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

    # Verified labs: the K16S exam server the owner runs (see docs/labs-k16s.md). Unset means
    # verified labs explain that no backend is configured; nothing is installed from here.
    k16s_base_url: str = ""
    # What the browser opens for the terminal and the exam UI; defaults to the base URL. In the
    # ring the pod and the browser reach the VM by different paths.
    k16s_public_url: str = ""
    # Optional link to a cluster map (Headlamp or similar), opened in a new tab.
    headlamp_url: str = ""

    # AWS labs: the LocalEmu emulator the owner runs in the lab (rex/istari#85). Unset means
    # AWS labs explain that no emulator is configured. Never a real AWS endpoint: the client
    # refuses amazonaws.com, and Istari holds no AWS credentials.
    localemu_base_url: str = ""
    localemu_region: str = "us-east-1"
    # The emulator's identity is the access key id and it checks no signature. Empty means its
    # root, AWS's documentation example id: a published placeholder, not a credential.
    localemu_access_key_id: str = ""

    @property
    def k16s_browser_url(self) -> str:
        return (self.k16s_public_url or self.k16s_base_url).rstrip("/")

    @model_validator(mode="after")
    def default_test_database_url(self) -> Settings:
        if not self.test_database_url:
            parts = urlsplit(self.database_url)
            self.test_database_url = urlunsplit(parts._replace(path=f"{parts.path}_test"))
        return self


settings = Settings()
