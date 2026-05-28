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
