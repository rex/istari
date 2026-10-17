"""boto3 clients pointed at the LocalEmu emulator, and botocore's failures as owner sentences.

Istari never talks to real AWS: the endpoint is always the emulator's, an amazonaws.com
endpoint is refused, and the credentials are the emulator's placeholder pair, never the
environment's (boto3's default chain is bypassed by passing both halves explicitly).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from app.domain.exceptions import UpstreamError

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client
    from types_boto3_sts.client import STSClient

# LocalEmu checks no signatures: identity is the access key id, so the key requests are
# signed with is a placeholder the emulator ignores.
UNCHECKED_SIGNING_KEY = "localemu-checks-no-signature"

_REAL_AWS_SUFFIXES = (".amazonaws.com", ".amazonaws.com.cn", ".api.aws")


@dataclass(frozen=True, slots=True)
class LocalEmuTimeouts:
    """Seconds, and botocore's total attempts per call (bounded retries)."""

    read: float = 10.0
    connect: float = 5.0
    api: float = 30.0
    attempts: int = 2


DEFAULT_TIMEOUTS = LocalEmuTimeouts()


@dataclass(frozen=True, slots=True)
class Aws:
    """boto3 clients for one emulator. `endpoint_url` is None only under moto, in tests."""

    session: boto3.Session
    endpoint_url: str | None
    config: Config

    def s3(self) -> S3Client:
        return self.session.client("s3", endpoint_url=self.endpoint_url, config=self.config)

    def sts(self) -> STSClient:
        return self.session.client("sts", endpoint_url=self.endpoint_url, config=self.config)


def emulator_endpoint(base_url: str) -> str:
    """The base URL without its trailing slash; refuses anything that is not an emulator."""
    host = (urlsplit(base_url).hostname or "").lower()
    if not host:
        raise ValueError(f"LOCALEMU_BASE_URL '{base_url}' has no host")
    if host == "amazonaws.com" or host.endswith(_REAL_AWS_SUFFIXES):
        raise ValueError(
            f"LOCALEMU_BASE_URL '{base_url}' is a real AWS endpoint; "
            "Istari only talks to the LocalEmu emulator"
        )
    return base_url.rstrip("/")


def emulator_aws(
    endpoint_url: str, *, region: str, access_key_id: str, timeouts: LocalEmuTimeouts
) -> Aws:
    session = boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=UNCHECKED_SIGNING_KEY,
        region_name=region,
    )
    config = Config(
        connect_timeout=timeouts.connect,
        read_timeout=timeouts.api,
        retries={"total_max_attempts": timeouts.attempts, "mode": "standard"},
        # The emulator has no per-bucket host names, and checksums are only sent when an
        # operation requires them, as emulators expect.
        s3={"addressing_style": "path"},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )
    return Aws(session=session, endpoint_url=endpoint_url, config=config)


# What a scenario's boto3 calls may raise that is the emulator's doing, not a bug in Istari.
AWS_ERRORS = (BotoCoreError, ClientError)


def upstream_error(
    base_url: str, exc: BotoCoreError | ClientError, *, doing: str, timeouts: LocalEmuTimeouts
) -> UpstreamError:
    """The sentence an owner can act on, for a failure while the emulator was `doing` a step."""
    where = f"LocalEmu at {base_url}"
    if isinstance(exc, ConnectTimeoutError | ReadTimeoutError):
        return UpstreamError(f"{where} did not answer within {timeouts.api:g} s ({doing})")
    if isinstance(exc, EndpointConnectionError | ConnectionClosedError):
        return UpstreamError(f"{where} is not reachable ({doing}): {exc}")
    if isinstance(exc, ClientError):
        error = exc.response.get("Error", {})
        code = str(error.get("Code", "")) or "error"
        message = str(error.get("Message", "")) or str(exc)
        return UpstreamError(
            f"{where} refused {doing}: {code}: {message}",
            details={"code": code, "step": doing},
        )
    return UpstreamError(f"{where} failed ({doing}): {exc}")
