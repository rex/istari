"""Declarative base with a constraint naming convention (stable Alembic names)."""

from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar

from sqlalchemy import Date, DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

JsonDict = dict[str, object]
JsonList = list[object]


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[object, object]] = {
        datetime: DateTime(timezone=True),
        date: Date(),
        JsonDict: JSONB,
        JsonList: JSONB,
        list[str]: JSONB,
        list[int]: JSONB,
        list[float]: JSONB,
    }


class TimestampMixin:
    """`created_at` / `updated_at` in UTC, maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
