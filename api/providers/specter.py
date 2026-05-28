"""In-process Specter provider. Reads fixtures/<domain>/specter.json.

For Phase 2+ the real Specter API client lives in the standalone specter-mcp
server (see mcp_servers/specter_mcp/). The two have the same shape; the
orchestrator can swap them transparently.
"""
import json
from pathlib import Path

from api.providers.base import ProviderResult


class SpecterProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "specter.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        normalized = self._normalize(raw, domain)
        return ProviderResult(source="specter", raw=raw, normalized=normalized)

    def _normalize(self, raw: dict, domain: str) -> dict:
        funding = raw.get("funding", {})
        hq = raw.get("hq", {})
        return {
            "domain": domain,
            "specter_id": raw.get("id"),
            "description": raw.get("description"),
            "operating_status": raw.get("operating_status", "active"),
            "tags": raw.get("tags"),
            "customer_focus": raw.get("customer_focus"),
            "customer_profile": raw.get("customer_profile"),
            "founded_year": raw.get("founded_year"),
            "hq_city": hq.get("city"),
            "hq_country": hq.get("country"),
            "hq_region": hq.get("region"),
            "certifications": raw.get("certifications"),
            "traction_highlights": raw.get("traction_highlights"),
            "technologies": raw.get("technologies"),
            "total_raised_usd": funding.get("total_raised_usd"),
            "last_round_type": funding.get("last_round_type"),
            "last_round_date": funding.get("last_round_date"),
            "last_round_usd": funding.get("last_round_usd"),
            "post_money_valuation_usd": funding.get("post_money_valuation_usd"),
            "round_count": funding.get("round_count"),
            "growth_stage": raw.get("growth_stage"),
            "investors": raw.get("investors"),
            "revenue_estimate_usd": raw.get("revenue_estimate_usd"),
        }
