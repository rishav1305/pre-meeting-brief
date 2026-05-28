"""Tests for the LangGraph orchestrator (Phase 2, Task 2.9).

The graph wires every Wave D agent + the deterministic nodes into one
pipeline. We do NOT touch real Postgres or the real Anthropic API here.
Each node is patched at its import site inside ``api.pipeline.graph``
so the graph's wiring (entry, conditional skip, sequencing) is the thing
under test, not the agents themselves (those have their own test files).
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from api.pipeline.graph import build_graph, run_pipeline
from api.pipeline.state import BriefState


# ─────────────────────────────────────────────────────────────────────────────
# Mock node factories — each one mutates the state predictably so the test
# can assert which nodes ran by inspecting state.timings.
# ─────────────────────────────────────────────────────────────────────────────


def _mock_resolve(decision_company_id=None):
    cid = decision_company_id or uuid4()

    async def _resolve(state: BriefState) -> BriefState:
        state.company_id = cid
        state.run_id = uuid4()
        state.timings["resolve_company"] = 0.001
        return state

    return _resolve


def _mock_qualification(decision: str = "proceed"):
    async def _qual(state: BriefState) -> BriefState:
        state.qualification = decision  # type: ignore[assignment]
        state.qualification_reason = f"mocked {decision}"
        state.timings["qualification"] = 0.001
        return state

    return _qual


async def _mock_fetch_all(state: BriefState) -> BriefState:
    state.specter_raw = {"domain": state.domain}
    state.crunchbase_raw = {"domain": state.domain}
    state.pitchbook_raw = {"domain": state.domain}
    state.attio_raw = {"domain": state.domain, "interactions": []}
    state.timings["fetch_all"] = 0.002
    return state


async def _mock_research(state: BriefState) -> BriefState:
    state.web_raw = "mocked research"
    state.web_citations = [{"title": "x", "url": "https://x.test", "snippet": ""}]
    state.timings["research"] = 0.002
    return state


async def _mock_merge(state: BriefState) -> BriefState:
    state.company_profile = {"name": state.company_name, "domain": state.domain}
    state.team_people = {"founders": []}
    state.traction_signals = {"highlights": []}
    state.funding_history = {"rounds": []}
    state.data_quality_flags = []
    state.timings["merge"] = 0.001
    return state


async def _mock_data_quality(state: BriefState) -> BriefState:
    state.dq_ranked = list(state.data_quality_flags)
    state.timings["data_quality"] = 0.001
    return state


def _mock_synthesise(failure: bool = False):
    async def _syn(state: BriefState) -> BriefState:
        if failure:
            state.error = "mocked synthesis failure"
            state.brief_json = None
            state.brief_html = None
        else:
            state.brief_json = {
                "snapshot": {"hook": "mocked"},
                "thesis_fit": {"score": 4, "reasoning": "x", "bear_case": "y"},
                "industry_deepdive": "",
                "market_deepdive": "",
                "key_engagement_questions": ["q1"],
                "podcast_mentions": [],
                "prior_interactions": [],
            }
            state.brief_html = "<article>mocked</article>"
        state.timings["synthesise"] = 0.001
        return state

    return _syn


def _mock_render_and_persist(failure: bool = False):
    async def _render(state: BriefState) -> BriefState:
        if state.brief_json is not None:
            state.brief_id = uuid4()
        # else: render still runs but doesn't set brief_id (closes run log as failed)
        state.timings["render_persist"] = 0.001
        return state

    return _render


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_graph_builds_without_error():
    """The graph compiles. Smoke that all node references resolve."""
    compiled = build_graph()
    assert compiled is not None
    # CompiledStateGraph supports ainvoke
    assert hasattr(compiled, "ainvoke")


async def test_pipeline_proceeds_through_all_nodes():
    """qualification=proceed: every node runs and brief_id is populated."""
    state_args = dict(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 30),
        partner="Devon",
    )

    with patch("api.pipeline.graph.resolve_company", new=_mock_resolve()), \
         patch("api.pipeline.graph.qualification_agent", new=_mock_qualification("proceed")), \
         patch("api.pipeline.graph.fetch_all", new=_mock_fetch_all), \
         patch("api.pipeline.graph.research_agent", new=_mock_research), \
         patch("api.pipeline.graph._merge_node", new=_mock_merge), \
         patch("api.pipeline.graph.data_quality_agent", new=_mock_data_quality), \
         patch("api.pipeline.graph.synthesise_brief", new=_mock_synthesise()), \
         patch("api.pipeline.graph.render_and_persist", new=_mock_render_and_persist()):
        out = await run_pipeline(**state_args)

    assert isinstance(out, BriefState)
    assert out.qualification == "proceed"
    assert out.brief_id is not None
    assert out.brief_json is not None
    # All seven non-skip nodes ran
    for node_key in (
        "resolve_company",
        "qualification",
        "fetch_all",
        "research",
        "merge",
        "data_quality",
        "synthesise",
        "render_persist",
    ):
        assert node_key in out.timings, f"missing timing for {node_key}"


async def test_pipeline_skips_on_qualification():
    """qualification=skip: fetch_all + downstream nodes do NOT run."""
    state_args = dict(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 30),
        partner="Devon",
    )

    with patch("api.pipeline.graph.resolve_company", new=_mock_resolve()), \
         patch("api.pipeline.graph.qualification_agent", new=_mock_qualification("skip")), \
         patch("api.pipeline.graph.fetch_all", new=_mock_fetch_all), \
         patch("api.pipeline.graph.research_agent", new=_mock_research), \
         patch("api.pipeline.graph._merge_node", new=_mock_merge), \
         patch("api.pipeline.graph.data_quality_agent", new=_mock_data_quality), \
         patch("api.pipeline.graph.synthesise_brief", new=_mock_synthesise()), \
         patch("api.pipeline.graph.render_and_persist", new=_mock_render_and_persist()):
        out = await run_pipeline(**state_args)

    assert out.qualification == "skip"
    assert out.brief_id is None
    assert out.brief_json is None
    # resolve_company + qualification ran; nothing else did
    assert "resolve_company" in out.timings
    assert "qualification" in out.timings
    for node_key in ("fetch_all", "research", "merge", "data_quality", "synthesise", "render_persist"):
        assert node_key not in out.timings, f"unexpectedly ran {node_key} after skip"


async def test_pipeline_handles_synthesis_failure_gracefully():
    """Synthesis sets brief_json=None: render_and_persist still runs without raising."""
    state_args = dict(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 30),
        partner="Devon",
    )

    with patch("api.pipeline.graph.resolve_company", new=_mock_resolve()), \
         patch("api.pipeline.graph.qualification_agent", new=_mock_qualification("proceed")), \
         patch("api.pipeline.graph.fetch_all", new=_mock_fetch_all), \
         patch("api.pipeline.graph.research_agent", new=_mock_research), \
         patch("api.pipeline.graph._merge_node", new=_mock_merge), \
         patch("api.pipeline.graph.data_quality_agent", new=_mock_data_quality), \
         patch("api.pipeline.graph.synthesise_brief", new=_mock_synthesise(failure=True)), \
         patch("api.pipeline.graph.render_and_persist", new=_mock_render_and_persist(failure=True)):
        out = await run_pipeline(**state_args)

    assert out.brief_json is None
    assert out.brief_id is None
    assert out.error == "mocked synthesis failure"
    # render_persist still ran
    assert "render_persist" in out.timings


async def test_pipeline_records_timings():
    """Every node that runs leaves an entry in state.timings."""
    state_args = dict(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 30),
        partner="Devon",
    )

    with patch("api.pipeline.graph.resolve_company", new=_mock_resolve()), \
         patch("api.pipeline.graph.qualification_agent", new=_mock_qualification("proceed")), \
         patch("api.pipeline.graph.fetch_all", new=_mock_fetch_all), \
         patch("api.pipeline.graph.research_agent", new=_mock_research), \
         patch("api.pipeline.graph._merge_node", new=_mock_merge), \
         patch("api.pipeline.graph.data_quality_agent", new=_mock_data_quality), \
         patch("api.pipeline.graph.synthesise_brief", new=_mock_synthesise()), \
         patch("api.pipeline.graph.render_and_persist", new=_mock_render_and_persist()):
        out = await run_pipeline(**state_args)

    assert len(out.timings) >= 8
    for v in out.timings.values():
        assert isinstance(v, (int, float))
        assert v >= 0
