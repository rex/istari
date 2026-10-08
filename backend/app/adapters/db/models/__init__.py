"""ORM models. Import this package so `Base.metadata` sees every table."""

from __future__ import annotations

from app.adapters.db.base import Base
from app.adapters.db.models.auth import AuthSession, LoginAttempt, Owner
from app.adapters.db.models.content import (
    ContentItem,
    ContentItemObjective,
    ContentPack,
    ContentRevision,
)
from app.adapters.db.models.notes import ItemProgress, LabEvidence, Note
from app.adapters.db.models.review import ReviewCard, ReviewEvent, SchedulerConfig
from app.adapters.db.models.settings import UserSettings
from app.adapters.db.models.study import Answer, SessionItem, StudySession
from app.adapters.db.models.track import Certification, Domain, ExamVersion, Objective, Subject
from app.adapters.db.models.watch import CourseProgress

__all__ = [
    "Answer",
    "AuthSession",
    "Base",
    "Certification",
    "ContentItem",
    "ContentItemObjective",
    "ContentPack",
    "ContentRevision",
    "CourseProgress",
    "Domain",
    "ExamVersion",
    "ItemProgress",
    "LabEvidence",
    "LoginAttempt",
    "Note",
    "Objective",
    "Owner",
    "ReviewCard",
    "ReviewEvent",
    "SchedulerConfig",
    "SessionItem",
    "StudySession",
    "Subject",
    "UserSettings",
]
