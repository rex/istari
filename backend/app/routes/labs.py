"""Lab briefs and evidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.contracts.common import OkResponse
from app.contracts.lab import EvidenceCreate, EvidenceView, LabSummary, LabView
from app.deps import ActiveExam, DbSession, ObjectiveMap, require_auth
from app.services import labs as lab_service

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("", response_model=list[LabSummary])
async def list_all(
    db: DbSession, exam: ActiveExam, objective_map: ObjectiveMap
) -> list[LabSummary]:
    return await lab_service.list_labs(db, exam_version_id=exam.id, objective_map=objective_map)


@router.get("/{key}", response_model=LabView)
async def read(key: str, db: DbSession, objective_map: ObjectiveMap) -> LabView:
    return await lab_service.get_lab(db, key=key, objective_map=objective_map)


@router.post("/{key}/evidence", response_model=EvidenceView, status_code=status.HTTP_201_CREATED)
async def add_evidence(key: str, req: EvidenceCreate, db: DbSession) -> EvidenceView:
    return await lab_service.add_evidence(db, key=key, req=req)


@router.patch("/evidence/{evidence_id}", response_model=EvidenceView)
async def update_evidence(evidence_id: int, req: EvidenceCreate, db: DbSession) -> EvidenceView:
    return await lab_service.update_evidence(db, evidence_id=evidence_id, req=req)


@router.delete("/evidence/{evidence_id}", response_model=OkResponse)
async def delete_evidence(evidence_id: int, db: DbSession) -> OkResponse:
    await lab_service.delete_evidence(db, evidence_id=evidence_id)
    return OkResponse()
