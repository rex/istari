"""A stand-in for the LocalEmu emulator in tests: its health endpoint, and moto for the rest.

The client reads only `/_localemu/health` over plain HTTP; that is served here through an
`httpx.MockTransport`, so up, down, silent and unhealthy are one field away. Scenario calls go
to moto's in-process `mock_aws` (LocalEmu is moto-derived), which intercepts only AWS's own
endpoints, so the test clients are built with no endpoint at all.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import httpx

from app.adapters.localemu import ROOT_ACCESS_KEY_ID, Aws, LocalEmuClient
from app.adapters.localemu.aws import DEFAULT_TIMEOUTS, emulator_aws

EMULATOR_URL = "http://localemu.test:4566"

# A trimmed copy of the real body (community 1.2.0 serves 133 services).
HEALTH_BODY = {
    "edition": "community",
    "version": "1.2.0",
    "services": {"s3": "available", "sts": "available"},
    "uptime": 42,
}

HealthMode = Literal["up", "down", "silent", "unhealthy"]


@dataclass
class EmulatorState:
    mode: HealthMode = "up"
    health_fetches: int = 0


def health_transport(state: EmulatorState) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path != "/_localemu/health":
            return httpx.Response(404, json={"error": f"no route {request.url.path}"})
        state.health_fetches += 1
        if state.mode == "down":
            raise httpx.ConnectError("connection refused", request=request)
        if state.mode == "silent":
            raise httpx.ReadTimeout("no answer", request=request)
        if state.mode == "unhealthy":
            return httpx.Response(503, text="starting")
        return httpx.Response(200, json=HEALTH_BODY)

    return httpx.MockTransport(handle)


def moto_aws() -> Aws:
    """The emulator's session and config with no endpoint, for use inside `mock_aws`."""
    aws = emulator_aws(
        EMULATOR_URL,
        region="us-east-1",
        access_key_id=ROOT_ACCESS_KEY_ID,
        timeouts=DEFAULT_TIMEOUTS,
    )
    return replace(aws, endpoint_url=None)


def stub_localemu(state: EmulatorState, aws: Aws | None = None) -> LocalEmuClient:
    """A client whose health goes to the stub and whose scenarios go to moto."""
    http = httpx.AsyncClient(transport=health_transport(state))
    return LocalEmuClient(EMULATOR_URL, http=http, aws=aws or moto_aws())
