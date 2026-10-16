"""Learning paths per objective: read, recompose, and the owner's decisions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.contracts.paths import ObjectivePathView, PathDecision, PathsView
from app.deps import ActiveExam, ClockDep, DbSession, require_auth
from app.services.catalog import CatalogCache
from app.services.learning_path import compose_paths, decide_path, objective_path, path_summaries

router = APIRouter(dependencies=[Depends(require_auth)])


def _catalog(request: Request) -> CatalogCache:
    catalog: CatalogCache = request.app.state.catalog
    return catalog


@router.get("", response_model=PathsView)
async def list_paths(db: DbSession, exam: ActiveExam) -> PathsView:
    return await path_summaries(db, exam)


@router.post("/rebuild", response_model=PathsView)
async def rebuild(request: Request, db: DbSession, exam: ActiveExam, clock: ClockDep) -> PathsView:
    """Recompose every objective's path from the current index; pins and exclusions stay."""
    return await compose_paths(db, _catalog(request), exam, now=clock.now())


@router.get("/{code}", response_model=ObjectivePathView)
async def read_path(
    code: str, request: Request, db: DbSession, exam: ActiveExam
) -> ObjectivePathView:
    return await objective_path(db, _catalog(request), exam, code)


@router.post("/{code}", response_model=ObjectivePathView)
async def decide(
    code: str, req: PathDecision, request: Request, db: DbSession, exam: ActiveExam, clock: ClockDep
) -> ObjectivePathView:
    return await decide_path(db, _catalog(request), exam, code, req, now=clock.now())
