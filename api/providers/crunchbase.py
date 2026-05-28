"""In-process Crunchbase provider. Reads fixtures/<domain>/crunchbase.json.

For Phase 2+ a real Crunchbase API client can be swapped in; the shape of the
normalized output is the contract.
"""
import json
from pathlib import Path

from api.providers.base import ProviderResult


class CrunchbaseProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "crunchbase.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        normalized = self._normalize(raw, domain)
        return ProviderResult(source="crunchbase", raw=raw, normalized=normalized)

    def _normalize(self, raw: dict, domain: str) -> dict:
        org = raw.get("org", {})
        return {
            "domain": domain,
            "cb_uuid": org.get("uuid"),
            "description": org.get("short_description"),
            "founded_year": org.get("founded_year"),
            "hq_country": org.get("country_code"),
            "hq_city": org.get("city"),
            "operating_status": org.get("operating_status"),
            "linkedin_url": org.get("linkedin_url"),
            "rounds": raw.get("rounds", []),
            "board_members": raw.get("board_members_and_advisors", []),
        }
