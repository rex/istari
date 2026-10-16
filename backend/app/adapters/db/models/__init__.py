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
from app.adapters.db.models.lectures import (
    IndexedLecture,
    LectureIndexRun,
    LectureObjective,
    LectureReview,
)
from app.adapters.db.models.notes import ItemProgress, LabAttempt, LabEvidence, Note
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
    "IndexedLecture",
    "ItemProgress",
    "LabAttempt",
    "LabEvidence",
    "LectureIndexRun",
    "LectureObjective",
    "LectureReview",
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
