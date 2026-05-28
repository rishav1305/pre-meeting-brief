"""In-process Attio provider. Reads fixtures/<domain>/attio.json.

For Phase 2+ a real Attio API client can be swapped in; the shape of the
normalized output is the contract.
"""
import json
from pathlib import Path

from api.providers.base import ProviderResult


class AttioProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "attio.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        normalized = self._normalize(raw, domain)
        return ProviderResult(source="attio", raw=raw, normalized=normalized)

    def _normalize(self, raw: dict, domain: str) -> dict:
        return {
            "domain": domain,
            "attio_company_id": raw.get("company_id"),
            "interactions": raw.get("interactions", []),
            "stage": raw.get("stage"),
            "last_interaction_date": raw.get("last_interaction_date"),
        }
