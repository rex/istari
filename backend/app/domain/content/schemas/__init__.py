"""Pydantic models describing a content pack file (`content/packs/<slug>/pack.json`)."""

from __future__ import annotations

from app.domain.content.schemas.common import Provenance, SourceRef
from app.domain.content.schemas.items import (
    FlashcardSpec,
    LabSpec,
    LessonCheck,
    LessonSpec,
    OptionSpec,
    QuestionSpec,
)
from app.domain.content.schemas.pack import ContentPackSpec, PackMeta
from app.domain.content.schemas.track import (
    CertificationSpec,
    DomainSpec,
    ExamVersionSpec,
    ObjectiveSpec,
    SubjectSpec,
    VerificationSpec,
)
from app.domain.content.schemas.verifier import LabVerifierSpec

__all__ = [
    "CertificationSpec",
    "ContentPackSpec",
    "DomainSpec",
    "ExamVersionSpec",
    "FlashcardSpec",
    "LabSpec",
    "LabVerifierSpec",
    "LessonCheck",
    "LessonSpec",
    "ObjectiveSpec",
    "OptionSpec",
    "PackMeta",
    "Provenance",
    "QuestionSpec",
    "SourceRef",
    "SubjectSpec",
    "VerificationSpec",
]
