"""What an exam guide says is in and out of scope: its appendix of technologies and services."""

from __future__ import annotations

from pydantic import Field

from app.domain.content.schemas.common import NonEmpty, StrictModel


class ServiceGroupSpec(StrictModel):
    """One category of the guide's service appendix ("Analytics") and its services."""

    category: NonEmpty
    services: list[NonEmpty] = Field(min_length=1)


class ScopeSpec(StrictModel):
    """The guide's appendix: technologies and concepts that might appear, the in-scope
    services and the out-of-scope services. An empty scope says the pack author has not
    copied the appendix, not that nothing is in scope."""

    technologies: list[NonEmpty] = Field(default_factory=list)
    in_scope: list[ServiceGroupSpec] = Field(default_factory=list)
    out_of_scope: list[ServiceGroupSpec] = Field(default_factory=list)
