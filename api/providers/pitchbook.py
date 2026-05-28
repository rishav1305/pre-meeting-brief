"""In-process PitchBook provider. Reads fixtures/<domain>/pitchbook.json.

For Phase 2+ a real PitchBook API client can be swapped in; the shape of the
normalized output is the contract.
"""
import json
from pathlib import Path

from api.providers.base import ProviderResult


class PitchBookProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "pitchbook.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        normalized = self._normalize(raw, domain)
        return ProviderResult(source="pitchbook", raw=raw, normalized=normalized)

    def _normalize(self, raw: dict, domain: str) -> dict:
        return {
            "domain": domain,
            "pb_id": raw.get("pb_id"),
            "total_raised_usd": raw.get("total_raised_usd"),
            "last_round_type": raw.get("last_round_type"),
            "last_round_date": raw.get("last_round_date"),
            "last_round_usd": raw.get("last_round_usd"),
            "post_money_valuation_usd": raw.get("post_money_valuation_usd"),
        }
