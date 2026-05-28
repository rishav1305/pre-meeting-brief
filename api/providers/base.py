"""DataProvider base interface and ProviderResult shape.

Every external data source (Specter, Crunchbase, PitchBook, Attio, web,
Notion) implements the :class:`DataProvider` Protocol so the orchestrator
can treat them uniformly. Results are returned as :class:`ProviderResult`,
which always carries both the raw payload (for replay/debug) and a
normalized projection (for downstream merging).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

Source = Literal["specter", "crunchbase", "pitchbook", "attio", "web", "notion"]


class ProviderResult(BaseModel):
    """Uniform envelope returned by every :class:`DataProvider`.

    ``raw`` holds the upstream payload verbatim (for ``source_payloads``
    replay), ``normalized`` holds the canonicalized projection the merger
    consumes, and ``error`` is set when the provider could not fulfill
    the request (e.g. company not found, rate-limited, auth failure).
    """

    source: Source
    raw: dict
    normalized: dict
    pulled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


@runtime_checkable
class DataProvider(Protocol):
    """Async contract every data source adapter must satisfy.

    Implementations receive a company ``domain`` plus a free-form
    ``hints`` dict (e.g. ``{"name": "Acme", "linkedin": "..."}``) and
    return a :class:`ProviderResult` or ``None`` when nothing matched.
    """

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        ...
