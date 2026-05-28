"""CLI: ``python -m eval.runner`` — runs eval against the latest brief per company.

Usage:
    python -m eval.runner                  # score latest brief per company in goldens
    python -m eval.runner --company anduril.com
    python -m eval.runner --regenerate     # re-run pipeline first, then score

Output: writes a timestamped JSON report to ``eval/reports/`` and prints a
summary table to stdout. Honors ``ANTHROPIC_API_KEY`` / ``ANTHROPIC_BASE_URL``
from env — same gateway the synthesis agent uses.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from api.db.models import Company, PreMeetingBrief
from api.db.session import SessionLocal
from eval.rubric import judge_brief, total_score


GOLDEN_PATH = Path(__file__).parent / "golden" / "criteria.json"
REPORTS_DIR = Path(__file__).parent / "reports"


def _load_goldens() -> dict[str, Any]:
    return json.loads(GOLDEN_PATH.read_text())


async def _latest_brief_for_domain(domain: str) -> dict[str, Any] | None:
    """Fetch the latest persisted brief for a given company domain.

    Returns a dict shaped like the /api/briefs/{id} response (so the judge
    sees the same brief the partner does). Returns None if no brief exists.
    """
    async with SessionLocal() as session:
        company = await session.scalar(
            select(Company).where(Company.domain == domain)
        )
        if company is None:
            return None
        brief = await session.scalar(
            select(PreMeetingBrief)
            .where(PreMeetingBrief.company_id == company.company_id)
            .order_by(PreMeetingBrief.generated_ts.desc())
            .limit(1)
        )
        if brief is None:
            return None
        return {
            "brief_id": str(brief.brief_id),
            "partner": brief.partner,
            "meeting_date": brief.meeting_date.isoformat(),
            "generated_at": brief.generated_ts.isoformat(),
            "thesis_fit": brief.thesis_fit,
            "industry_deepdive": brief.industry_deepdive,
            "market_deepdive": brief.market_deepdive,
            "key_engagement_questions": brief.key_engagement_questions,
            "podcast_mentions": brief.podcast_mentions,
            "prior_interactions": brief.prior_interactions,
            "audit_company": brief.audit_company,
            "audit_people": brief.audit_people,
            "audit_traction_metrics": brief.audit_traction_metrics,
        }


async def run_eval(filter_domain: str | None = None) -> dict[str, Any]:
    goldens = _load_goldens()
    results: list[dict[str, Any]] = []

    for company_spec in goldens["companies"]:
        domain = company_spec["domain"]
        if filter_domain and domain != filter_domain:
            continue

        brief = await _latest_brief_for_domain(domain)
        if brief is None:
            results.append({
                "domain": domain,
                "status": "no_brief_found",
                "scores": None,
                "total": None,
            })
            continue

        try:
            scores = judge_brief(
                criteria={"axes": goldens["axes"], "company": company_spec},
                brief=brief,
            )
            results.append({
                "domain": domain,
                "brief_id": brief["brief_id"],
                "status": "scored",
                "scores": scores,
                "total": total_score(scores),
            })
        except Exception as exc:  # noqa: BLE001
            results.append({
                "domain": domain,
                "brief_id": brief["brief_id"],
                "status": "judge_error",
                "error": str(exc),
                "scores": None,
                "total": None,
            })

    report = {
        "version": goldens["version"],
        "ran_at": datetime.utcnow().isoformat() + "Z",
        "results": results,
        "summary": {
            "scored": sum(1 for r in results if r["status"] == "scored"),
            "no_brief": sum(1 for r in results if r["status"] == "no_brief_found"),
            "errors": sum(1 for r in results if r["status"] == "judge_error"),
            "avg_total": (
                sum(r["total"] for r in results if r["total"] is not None)
                / max(sum(1 for r in results if r["total"] is not None), 1)
            ),
        },
    }
    return report


def _print_table(report: dict[str, Any]) -> None:
    print()
    print(f"Eval report — goldens version {report['version']}, ran {report['ran_at']}")
    print("=" * 78)
    print(f"{'Domain':<24} {'Status':<16} {'Total':>6}  {'Axes (FA/PE/QS/CD/LC)':<22}")
    print("-" * 78)
    for r in report["results"]:
        domain = r["domain"]
        status = r["status"]
        total = r["total"]
        axes_str = ""
        if r["scores"]:
            s = r["scores"]
            axes_str = (
                f"{s.get('factual_accuracy',{}).get('score','?')}/"
                f"{s.get('prior_engagement_coherence',{}).get('score','?')}/"
                f"{s.get('question_sharpness',{}).get('score','?')}/"
                f"{s.get('citation_discipline',{}).get('score','?')}/"
                f"{s.get('language_calibration',{}).get('score','?')}"
            )
        print(f"{domain:<24} {status:<16} {str(total):>6}  {axes_str:<22}")
    print("-" * 78)
    summary = report["summary"]
    print(
        f"Scored: {summary['scored']} | No brief: {summary['no_brief']} | "
        f"Errors: {summary['errors']} | Avg total: {summary['avg_total']:.1f}/25"
    )
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run brief-quality eval")
    parser.add_argument(
        "--company",
        type=str,
        default=None,
        help="filter to one domain (e.g. anduril.com)",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="do not write the report file (stdout only)",
    )
    args = parser.parse_args()

    report = asyncio.run(run_eval(filter_domain=args.company))
    _print_table(report)

    if not args.no_write:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = report["ran_at"].replace(":", "-").replace(".", "-")
        out_path = REPORTS_DIR / f"eval-{timestamp}.json"
        out_path.write_text(json.dumps(report, indent=2))
        print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
