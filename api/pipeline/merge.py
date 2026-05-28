"""Deterministic canonical merge — Phase 2 Task 2.3.

Applies the Data Dictionary's source-priority chains for the 3 canonical
entities (company, people, traction_metrics), emits CONFLICT-1..6 DQFlag rows,
and writes a JSONB audit trail to each entity dict under the ``audit`` key.

This is the agentic layer's source-of-truth on field provenance and conflict
detection. No LLM calls. Pure deterministic Python so the Data Quality Agent
downstream can reason about *prioritised* flags instead of re-running detection.

See ``docs/approach.md`` §7.4 for the priority chains and conflict thresholds.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from api.pipeline.state import BriefState, DQFlag


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# ENUM normalization for round-type values (sources differ in casing / hyphenation).
_ROUND_TYPE_NORMALIZER: dict[str, str] = {
    "angel": "angel",
    "pre-seed": "pre_seed",
    "pre_seed": "pre_seed",
    "preseed": "pre_seed",
    "seed": "seed",
    "series-a": "series_a",
    "series_a": "series_a",
    "series a": "series_a",
    "series-b": "series_b",
    "series_b": "series_b",
    "series b": "series_b",
    "series-c": "series_c",
    "series_c": "series_c",
    "series c": "series_c",
    "series-d": "series_d",
    "series_d": "series_d",
    "series d": "series_d",
    "series-e": "series_e",
    "series_e": "series_e",
    "series e": "series_e",
    "series-f": "series_f",
    "series_f": "series_f",
    "series f": "series_f",
    "series-g": "series_g",
    "series_g": "series_g",
    "series g": "series_g",
    "debt": "debt",
    "convertible": "convertible",
    "secondary": "secondary",
    "ipo": "ipo",
    "post-ipo": "post_ipo",
    "grant": "grant",
}

# Country code normalization (3-letter ISO → 2-letter).
_COUNTRY_NORMALIZER: dict[str, str] = {
    "USA": "US",
    "GBR": "UK",
    "GB": "UK",
    "CAN": "CA",
    "DEU": "DE",
    "FRA": "FR",
    "AUS": "AU",
    "IND": "IN",
    "JPN": "JP",
    "CHN": "CN",
}

# Crunchbase employee enum midpoints — used for CONFLICT-5 detection.
_CB_EMP_MIDPOINTS: dict[str, int] = {
    "1-10": 5,
    "11-50": 30,
    "51-100": 75,
    "101-250": 175,
    "251-500": 375,
    "501-1000": 750,
    "1001-5000": 3000,
    "5001-10000": 7500,
    "10001+": 15000,
}

# Specter highlight tags considered talent-related (hiring_signals projection).
_TALENT_TAGS: frozenset[str] = frozenset({
    "headcount_surge",
    "engineering_hiring",
    "ml_hiring",
    "executive_hiring",
    "sales_hiring",
})


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _normalize_round_type(val: str | None) -> str | None:
    if val is None:
        return None
    return _ROUND_TYPE_NORMALIZER.get(val.strip().lower(), val.strip().lower())


def _normalize_country(val: str | None) -> str | None:
    if val is None:
        return None
    return _COUNTRY_NORMALIZER.get(val, val)


def _audit(audit_list: list[dict], field: str, source: str) -> None:
    audit_list.append({"field": field, "source": source, "pulled_at": _now_iso()})


def _coalesce(
    audit_list: list[dict],
    field: str,
    candidates: list[tuple[str, Any]],
) -> Any:
    """First non-None wins; record the winning source in ``audit_list``.

    ``candidates`` is an ordered list of ``(source_name, value)`` tuples. If all
    values are None, the field is logged with source="missing" and returns None.
    """
    for source, val in candidates:
        if val is not None:
            _audit(audit_list, field, source)
            return val
    _audit(audit_list, field, "missing")
    return None


def _safe_get(d: dict | None, *keys: str, default: Any = None) -> Any:
    """Walk a nested dict; return ``default`` on any missing/None hop."""
    cur: Any = d
    for k in keys:
        if cur is None or not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _parse_iso_date(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        # tolerate both YYYY-MM-DD and full ISO
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _array_union_ci(
    primary: list[str] | None,
    secondary: list[str] | None,
) -> list[str]:
    """Union two lists, dedup case-insensitively, preserve primary casing first."""
    result: list[str] = []
    seen: set[str] = set()
    for item in (primary or []) + (secondary or []):
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Conflict detectors (CONFLICT-1..6)
# ─────────────────────────────────────────────────────────────────────────────


def _conflict_1_operating_status(
    flags: list[DQFlag], specter_val: str | None, cb_val: str | None
) -> None:
    if specter_val is not None and cb_val is not None and specter_val != cb_val:
        flags.append(DQFlag(
            field="operating_status",
            issue="specter != crunchbase",
            severity="high",
            source_a="specter", value_a=str(specter_val),
            source_b="crunchbase", value_b=str(cb_val),
        ))


def _conflict_2_founded_year(
    flags: list[DQFlag], specter_val: int | None, cb_val: int | None
) -> None:
    if specter_val is not None and cb_val is not None and abs(specter_val - cb_val) > 1:
        flags.append(DQFlag(
            field="founded_year",
            issue="delta > 1 year",
            severity="medium",
            source_a="specter", value_a=str(specter_val),
            source_b="crunchbase", value_b=str(cb_val),
        ))


def _conflict_3_hq_country(
    flags: list[DQFlag], specter_val: str | None, cb_val: str | None
) -> None:
    if specter_val is not None and cb_val is not None and specter_val != cb_val:
        flags.append(DQFlag(
            field="hq_country",
            issue="specter != crunchbase",
            severity="high",
            source_a="specter", value_a=str(specter_val),
            source_b="crunchbase", value_b=str(cb_val),
        ))


def _conflict_4_last_round_date(
    flags: list[DQFlag],
    pb_val: str | None,
    spec_val: str | None,
    cb_val: str | None,
) -> None:
    """Flag if any two sources have last_round_date delta > 30 days."""
    candidates: list[tuple[str, datetime]] = []
    for src, raw in (("pitchbook", pb_val), ("specter", spec_val), ("crunchbase", cb_val)):
        parsed = _parse_iso_date(raw)
        if parsed is not None:
            candidates.append((src, parsed))
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            src_a, val_a = candidates[i]
            src_b, val_b = candidates[j]
            delta_days = abs((val_a - val_b).days)
            if delta_days > 30:
                flags.append(DQFlag(
                    field="last_round_date",
                    issue=f"delta > 30 days ({delta_days})",
                    severity="high",
                    source_a=src_a, value_a=val_a.date().isoformat(),
                    source_b=src_b, value_b=val_b.date().isoformat(),
                ))
                return  # one flag suffices


def _conflict_5_employee_count(
    flags: list[DQFlag],
    specter_val: int | None,
    cb_enum: str | None,
) -> None:
    if specter_val is None or cb_enum is None:
        return
    mid = _CB_EMP_MIDPOINTS.get(cb_enum)
    if mid is None:
        return
    if specter_val > 2 * mid:
        flags.append(DQFlag(
            field="employee_count",
            issue=f"specter ({specter_val}) > 2x crunchbase midpoint ({mid})",
            severity="medium",
            source_a="specter", value_a=str(specter_val),
            source_b="crunchbase", value_b=cb_enum,
        ))


def _conflict_6_g2_rating(
    flags: list[DQFlag],
    specter_val: float | None,
    web_val: float | None,
) -> None:
    """Detector exists for code completeness — no POC fixtures trigger it."""
    if specter_val is None or web_val is None:
        return
    if abs(specter_val - web_val) > 0.5:
        flags.append(DQFlag(
            field="g2_rating",
            issue="specter vs web disagree",
            severity="low",
            source_a="specter", value_a=str(specter_val),
            source_b="web", value_b=str(web_val),
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Entity builders
# ─────────────────────────────────────────────────────────────────────────────


def _build_company_profile(
    state: BriefState, flags: list[DQFlag]
) -> dict:
    spec = state.specter_raw or {}
    cb = state.crunchbase_raw or {}
    pb = state.pitchbook_raw or {}

    audit: list[dict] = []
    cp: dict[str, Any] = {"domain": state.domain}
    _audit(audit, "domain", "input")

    # description
    cp["description"] = _coalesce(audit, "description", [
        ("specter", spec.get("description")),
        ("crunchbase", _safe_get(cb, "org", "short_description")),
    ])

    # operating_status — specter wins, conflict flag if different
    spec_status = spec.get("operating_status")
    cb_status = _safe_get(cb, "org", "operating_status")
    _conflict_1_operating_status(flags, spec_status, cb_status)
    cp["operating_status"] = _coalesce(audit, "operating_status", [
        ("specter", spec_status),
        ("crunchbase", cb_status),
    ])

    # tags — specter only
    cp["tags"] = _coalesce(audit, "tags", [("specter", spec.get("tags"))])

    # customer_focus / customer_profile — specter only
    cp["customer_focus"] = _coalesce(audit, "customer_focus", [("specter", spec.get("customer_focus"))])
    cp["customer_profile"] = _coalesce(audit, "customer_profile", [("specter", spec.get("customer_profile"))])

    # founded_year — COALESCE(specter, crunchbase) + CONFLICT-2
    spec_fy = spec.get("founded_year")
    cb_fy = _safe_get(cb, "org", "founded_year")
    _conflict_2_founded_year(flags, spec_fy, cb_fy)
    cp["founded_year"] = _coalesce(audit, "founded_year", [
        ("specter", spec_fy),
        ("crunchbase", cb_fy),
    ])

    # hq fields
    cp["hq_city"] = _coalesce(audit, "hq_city", [
        ("specter", _safe_get(spec, "hq", "city")),
        ("crunchbase", _safe_get(cb, "org", "city")),
    ])

    spec_country = _normalize_country(_safe_get(spec, "hq", "country"))
    cb_country = _normalize_country(_safe_get(cb, "org", "country_code"))
    _conflict_3_hq_country(flags, spec_country, cb_country)
    cp["hq_country"] = _coalesce(audit, "hq_country", [
        ("specter", spec_country),
        ("crunchbase", cb_country),
    ])

    cp["hq_region"] = _coalesce(audit, "hq_region", [
        ("specter", _safe_get(spec, "hq", "region")),
    ])

    # Funding fields — pitchbook is the source of truth, then specter, then crunchbase
    spec_funding = spec.get("funding") or {}
    cb_rounds = cb.get("rounds") or []
    cb_last = cb_rounds[0] if cb_rounds else {}

    cp["total_raised_usd"] = _coalesce(audit, "total_raised_usd", [
        ("pitchbook", pb.get("total_raised_usd")),
        ("specter", spec_funding.get("total_raised_usd")),
        ("crunchbase", sum(r.get("raised_usd") or 0 for r in cb_rounds) or None),
    ])

    cp["last_round_type"] = _normalize_round_type(_coalesce(audit, "last_round_type", [
        ("pitchbook", pb.get("last_round_type")),
        ("specter", spec_funding.get("last_round_type")),
        ("crunchbase", cb_last.get("investment_type")),
    ]))

    pb_date = pb.get("last_round_date")
    spec_date = spec_funding.get("last_round_date")
    cb_date = cb_last.get("announced_on")
    _conflict_4_last_round_date(flags, pb_date, spec_date, cb_date)
    cp["last_round_date"] = _coalesce(audit, "last_round_date", [
        ("pitchbook", pb_date),
        ("specter", spec_date),
        ("crunchbase", cb_date),
    ])

    cp["last_round_usd"] = _coalesce(audit, "last_round_usd", [
        ("pitchbook", pb.get("last_round_usd")),
        ("specter", spec_funding.get("last_round_usd")),
        ("crunchbase", cb_last.get("raised_usd")),
    ])

    cp["post_money_valuation_usd"] = _coalesce(audit, "post_money_valuation_usd", [
        ("pitchbook", pb.get("post_money_valuation_usd")),
        ("specter", spec_funding.get("post_money_valuation_usd")),
    ])

    cp["round_count"] = _coalesce(audit, "round_count", [
        ("specter", spec_funding.get("round_count")),
        ("crunchbase", len(cb_rounds) or None),
    ])

    cp["growth_stage"] = _coalesce(audit, "growth_stage", [
        ("specter", spec.get("growth_stage")),
    ])

    # investors — ARRAY_UNION(specter, crunchbase)
    spec_invs = spec.get("investors") or []
    cb_invs: list[str] = []
    for r in cb_rounds:
        for inv in r.get("investors") or []:
            cb_invs.append(inv)
    union = _array_union_ci(spec_invs, cb_invs)
    if union:
        cp["investors"] = union
        _audit(audit, "investors", "specter+crunchbase")
    elif spec_invs or cb_invs:
        cp["investors"] = union
        _audit(audit, "investors", "specter" if spec_invs else "crunchbase")
    else:
        cp["investors"] = None
        _audit(audit, "investors", "missing")

    cp["revenue_estimate_usd"] = _coalesce(audit, "revenue_estimate_usd", [
        ("specter", spec.get("revenue_estimate_usd")),
        ("pitchbook", pb.get("revenue_estimate_usd")),
    ])

    cp["audit"] = audit
    return cp


def _build_funding_history(state: BriefState, company_profile: dict) -> dict:
    cb = state.crunchbase_raw or {}
    spec = state.specter_raw or {}
    audit: list[dict] = []

    cb_rounds = cb.get("rounds") or []
    if cb_rounds:
        rounds = [
            {
                "announced_on": r.get("announced_on"),
                "investment_type": _normalize_round_type(r.get("investment_type")),
                "raised_usd": r.get("raised_usd"),
                "post_money_valuation_usd": r.get("post_money_valuation_usd"),
                "investors": r.get("investors") or [],
            }
            for r in cb_rounds
        ]
        _audit(audit, "rounds", "crunchbase")
    else:
        spec_f = spec.get("funding") or {}
        if spec_f:
            rounds = [{
                "announced_on": spec_f.get("last_round_date"),
                "investment_type": _normalize_round_type(spec_f.get("last_round_type")),
                "raised_usd": spec_f.get("last_round_usd"),
                "post_money_valuation_usd": spec_f.get("post_money_valuation_usd"),
                "investors": spec.get("investors") or [],
            }]
            _audit(audit, "rounds", "specter")
        else:
            rounds = []
            _audit(audit, "rounds", "missing")

    return {
        "rounds": rounds,
        "total_raised_usd": company_profile.get("total_raised_usd"),
        "audit": audit,
    }


def _build_team_people(state: BriefState, flags: list[DQFlag]) -> dict:
    spec = state.specter_raw or {}
    cb = state.crunchbase_raw or {}
    audit: list[dict] = []

    # Founders: merge by full_name (case-insensitive). Specter wins on title/linkedin.
    spec_founders = spec.get("founder_info") or []
    cb_founders = cb.get("founders") or []
    by_key: dict[str, dict] = {}
    for f in spec_founders:
        name = f.get("full_name") or ""
        key = name.lower().strip()
        if not key:
            continue
        by_key[key] = {
            "full_name": name,
            "title": f.get("title"),
            "linkedin_url": f.get("linkedin_url"),
            "prior_companies": f.get("prior_companies") or [],
            "prior_exits": f.get("prior_exits") or [],
            "source": "specter",
        }
    for f in cb_founders:
        name = f.get("full_name") or ""
        key = name.lower().strip()
        if not key:
            continue
        if key in by_key:
            # Specter already there; only fill genuinely-missing fields
            existing = by_key[key]
            if not existing.get("title") and f.get("title"):
                existing["title"] = f.get("title")
            if not existing.get("linkedin_url") and f.get("linkedin_url"):
                existing["linkedin_url"] = f.get("linkedin_url")
        else:
            by_key[key] = {
                "full_name": name,
                "title": f.get("title"),
                "linkedin_url": f.get("linkedin_url"),
                "prior_companies": f.get("prior_companies") or [],
                "prior_exits": f.get("prior_exits") or [],
                "source": "crunchbase",
            }
    founders = list(by_key.values())
    _audit(audit, "founders", "specter+crunchbase" if (spec_founders and cb_founders) else (
        "specter" if spec_founders else ("crunchbase" if cb_founders else "missing")
    ))

    # key_executives — specter only, filtered to Executive/VP Level
    key_people = spec.get("key_people") or []
    execs = [p for p in key_people if p.get("level") in ("Executive Level", "VP Level")]
    if execs:
        _audit(audit, "key_executives", "specter")
    else:
        _audit(audit, "key_executives", "missing")

    # board_members — crunchbase only
    board = cb.get("board_members_and_advisors") or []
    _audit(audit, "board_members", "crunchbase" if board else "missing")

    # employee_count + CONFLICT-5
    spec_emp = spec.get("employee_count")
    cb_enum = _safe_get(cb, "org", "num_employees_enum")
    _conflict_5_employee_count(flags, spec_emp, cb_enum)
    cb_mid = _CB_EMP_MIDPOINTS.get(cb_enum) if cb_enum else None
    employee_count = _coalesce(audit, "employee_count", [
        ("specter", spec_emp),
        ("crunchbase", cb_mid),
    ])

    employee_range = _coalesce(audit, "employee_range", [
        ("specter", spec.get("employee_count_range")),
    ])

    headcount_trend = _coalesce(audit, "headcount_trend", [
        ("specter", _safe_get(spec, "traction_metrics", "employee_count", "trend_6mo")),
    ])

    # hiring_signals: specter highlights filtered to talent-related tags,
    # plus the explicit hiring_signals field if present.
    spec_highlights = spec.get("highlights") or []
    spec_hiring = spec.get("hiring_signals") or []
    talent_filtered = [h for h in spec_highlights if h in _TALENT_TAGS]
    hiring_signals = list(dict.fromkeys(talent_filtered + spec_hiring)) or None
    if hiring_signals:
        _audit(audit, "hiring_signals", "specter")
    else:
        _audit(audit, "hiring_signals", "missing")

    open_role_count = _coalesce(audit, "open_role_count", [("specter", spec.get("open_role_count"))])
    org_rank = _coalesce(audit, "org_rank", [("specter", spec.get("org_rank"))])

    return {
        "founders": founders,
        "key_executives": execs,
        "board_members": board,
        "employee_count": employee_count,
        "employee_range": employee_range,
        "headcount_trend": headcount_trend,
        "hiring_signals": hiring_signals,
        "open_role_count": open_role_count,
        "org_rank": org_rank,
        "audit": audit,
    }


def _build_traction_signals(state: BriefState, flags: list[DQFlag]) -> dict:
    spec = state.specter_raw or {}
    audit: list[dict] = []

    out: dict[str, Any] = {}
    out["highlights"] = _coalesce(audit, "highlights", [("specter", spec.get("highlights"))])
    out["new_highlights"] = _coalesce(audit, "new_highlights", [("specter", spec.get("new_highlights"))])
    out["web_visits_latest"] = _coalesce(audit, "web_visits_latest", [
        ("specter", _safe_get(spec, "traction_metrics", "web_visits", "latest")),
    ])
    out["web_visits_trend"] = _coalesce(audit, "web_visits_trend", [
        ("specter", _safe_get(spec, "traction_metrics", "web_visits", "trend_3mo")),
    ])
    out["web_popularity_rank"] = _coalesce(audit, "web_popularity_rank", [
        ("specter", _safe_get(spec, "web", "popularity_rank")),
    ])
    out["bounce_rate"] = _coalesce(audit, "bounce_rate", [
        ("specter", _safe_get(spec, "web", "bounce_rate")),
    ])
    out["top_traffic_country"] = _coalesce(audit, "top_traffic_country", [
        ("specter", _safe_get(spec, "web", "top_country")),
    ])
    out["traffic_sources"] = _coalesce(audit, "traffic_sources", [
        ("specter", _safe_get(spec, "web", "traffic_source")),
    ])
    out["linkedin_followers"] = _coalesce(audit, "linkedin_followers", [
        ("specter", _safe_get(spec, "traction_metrics", "linkedin_followers", "latest")),
    ])
    out["linkedin_trend"] = _coalesce(audit, "linkedin_trend", [
        ("specter", _safe_get(spec, "traction_metrics", "linkedin_followers", "trend_6mo")),
    ])

    # G2 / Trustpilot — POC doesn't populate these in any fixture but they're DD fields.
    spec_g2_rating = _safe_get(spec, "reviews", "g2", "rating")
    out["g2_rating"] = _coalesce(audit, "g2_rating", [("specter", spec_g2_rating)])
    out["g2_review_count"] = _coalesce(audit, "g2_review_count", [
        ("specter", _safe_get(spec, "reviews", "g2", "review_count")),
    ])
    out["trustpilot_rating"] = _coalesce(audit, "trustpilot_rating", [
        ("specter", _safe_get(spec, "reviews", "trustpilot", "rating")),
    ])
    # CONFLICT-6: detector exists; no POC fixture supplies a web-derived g2 rating.
    _conflict_6_g2_rating(flags, spec_g2_rating, None)

    out["awards"] = _coalesce(audit, "awards", [("specter", spec.get("awards"))])
    out["patents"] = _coalesce(audit, "patents", [("specter", spec.get("patent_count"))])
    out["reported_clients"] = _coalesce(audit, "reported_clients", [("specter", spec.get("reported_clients"))])
    out["it_spend_usd"] = _coalesce(audit, "it_spend_usd", [("specter", spec.get("it_spend"))])

    # News union (specter + web parsed citations), dedup by URL, sort by date desc.
    spec_news = spec.get("news") or []
    web_news = state.web_citations or []
    news_by_url: dict[str, dict] = {}
    for item in spec_news + web_news:
        url = item.get("url")
        if url and url not in news_by_url:
            news_by_url[url] = item
    news = sorted(news_by_url.values(), key=lambda n: n.get("date") or "", reverse=True)
    out["news"] = news if news else None
    _audit(audit, "news", "specter+web" if (spec_news and web_news) else (
        "specter" if spec_news else ("web" if web_news else "missing")
    ))

    out["audit"] = audit
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Public entrypoint
# ─────────────────────────────────────────────────────────────────────────────


def merge_canonical(state: BriefState) -> BriefState:
    """Apply DD source-priority chains + emit conflict flags. Mutates and returns state."""
    flags: list[DQFlag] = []

    state.company_profile = _build_company_profile(state, flags)
    state.funding_history = _build_funding_history(state, state.company_profile)
    state.team_people = _build_team_people(state, flags)
    state.traction_signals = _build_traction_signals(state, flags)
    state.data_quality_flags = flags

    return state
