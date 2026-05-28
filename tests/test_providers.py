"""Tests for the DataProvider base interface and ProviderResult model."""
from __future__ import annotations

from api.providers.base import DataProvider, ProviderResult


def test_provider_result_shape() -> None:
    """ProviderResult can be constructed with source, raw, and normalized fields."""
    result = ProviderResult(
        source="specter",
        raw={"hello": "world"},
        normalized={"hello": "world"},
    )
    assert result.source == "specter"
    assert result.raw == {"hello": "world"}
    assert result.normalized == {"hello": "world"}
    assert result.error is None
    assert result.pulled_at is not None


def test_provider_result_with_error() -> None:
    """ProviderResult can carry an error string while raw/normalized stay empty."""
    result = ProviderResult(
        source="crunchbase",
        raw={},
        normalized={},
        error="company not found",
    )
    assert result.error == "company not found"
    assert result.source == "crunchbase"
    assert result.raw == {}
    assert result.normalized == {}


def test_data_provider_is_protocol() -> None:
    """A class with the right async fetch signature should satisfy the Protocol."""

    class FakeProvider:
        async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
            return ProviderResult(source="specter", raw={}, normalized={})

    fake_provider = FakeProvider()
    assert isinstance(fake_provider, DataProvider)


from pathlib import Path

import pytest

from api.providers.specter import SpecterProvider

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_specter_provider_hits_fixture():
    provider = SpecterProvider(fixtures_dir=FIXTURES_DIR)
    result = await provider.fetch("anduril.com", hints={})
    assert result is not None
    assert result.source == "specter"
    assert result.raw["organization_name"] == "Anduril Industries"
    assert result.normalized["domain"] == "anduril.com"
    assert result.normalized["founded_year"] == 2017


@pytest.mark.asyncio
async def test_specter_provider_returns_none_on_miss():
    provider = SpecterProvider(fixtures_dir=FIXTURES_DIR)
    result = await provider.fetch("notinfixtures.com", hints={})
    assert result is None
