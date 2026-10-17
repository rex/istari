"""Verified labs: the verifier's state, set up the environment, check the answer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.contracts.lab_verifier import CheckResponse, SetupResponse, VerifierStateView
from app.deps import ClockDep, DbSession, require_auth
from app.services import lab_verifier as service
from app.services.verifier_clients import VerifierClients

router = APIRouter(dependencies=[Depends(require_auth)])


def _clients(request: Request) -> VerifierClients:
    """Every configured backend; the service picks the one the lab's spec names."""
    clients: VerifierClients = request.app.state.verifiers
    return clients


@router.get("/{key}/verifier", response_model=VerifierStateView)
async def verifier(key: str, request: Request, db: DbSession) -> VerifierStateView:
    headlamp: str = request.app.state.headlamp_url
    return await service.state(db, key=key, clients=_clients(request), headlamp_url=headlamp)


@router.post("/{key}/setup", response_model=SetupResponse)
async def setup(key: str, request: Request, db: DbSession, clock: ClockDep) -> SetupResponse:
    return await service.setup(db, key=key, clients=_clients(request), now=clock.now())


@router.post("/{key}/check", response_model=CheckResponse)
async def check(key: str, request: Request, db: DbSession, clock: ClockDep) -> CheckResponse:
    return await service.check(db, key=key, clients=_clients(request), now=clock.now())
