"""LangGraph orchestrator — Phase 2 Task 2.9.

Wires the deterministic nodes + Wave D agents into one pipeline graph:

    resolve_company
      ↓
    qualification  ──(skip)──→  END
      ↓
    fetch_all
      ↓
    research
      ↓
    merge
      ↓
    data_quality
      ↓
    synthesise
      ↓
    render_persist
      ↓
    END

Phase 2 ships ``fetch_all`` → ``research`` serially. Each individual step's
concurrency (4 providers inside fetch_all; up to 5 web searches inside
research) is preserved. Parallelising the two branches via LangGraph's
``Send`` API is a Phase 3 optimisation once we have a stable baseline.

The graph state is :class:`BriefState`. Each node mutates and returns the
same state object; LangGraph diffs node outputs into the shared state.
``ainvoke`` returns a ``dict`` view of the final state — :func:`run_pipeline`
revalidates it back into a :class:`BriefState` so callers get a typed object.
"""
from __future__ import annotations

from datetime import date

from langgraph.graph import END, StateGraph

from api.pipeline.agents.data_quality import data_quality_agent
from api.pipeline.agents.qualification import qualification_agent
from api.pipeline.agents.research import research_agent
from api.pipeline.agents.synthesis import synthesise_brief
from api.pipeline.merge import merge_canonical
from api.pipeline.nodes import fetch_all, render_and_persist, resolve_company
from api.pipeline.state import BriefState


# ─────────────────────────────────────────────────────────────────────────────
# Wrappers
# ─────────────────────────────────────────────────────────────────────────────


async def _merge_node(state: BriefState) -> BriefState:
    """Async wrapper around the synchronous :func:`merge_canonical`.

    Defined at module level (not inline in :func:`build_graph`) so tests can
    monkey-patch it via ``patch("api.pipeline.graph._merge_node", new=...)``.
    """
    return merge_canonical(state)


def _qualification_route(state: BriefState) -> str:
    """Conditional edge after qualification.

    Returns the literal key into the path_map dict — ``"end"`` short-circuits
    the pipeline, ``"continue"`` flows into fetch_all. ``flag_for_human`` is
    treated as ``continue`` here: the brief still gets produced; the gating
    happens at agenda-display time.
    """
    if state.qualification == "skip":
        return "end"
    return "continue"


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────


def build_graph():
    """Build and compile the BriefState pipeline graph.

    Returns the compiled graph (a ``CompiledStateGraph``). Callers invoke it
    via ``await compiled.ainvoke(initial_state)``.
    """
    graph = StateGraph(BriefState)

    graph.add_node("resolve_company", resolve_company)
    graph.add_node("qualification", qualification_agent)
    graph.add_node("fetch_all", fetch_all)
    graph.add_node("research", research_agent)
    graph.add_node("merge", _merge_node)
    graph.add_node("data_quality", data_quality_agent)
    graph.add_node("synthesise", synthesise_brief)
    graph.add_node("render_persist", render_and_persist)

    graph.set_entry_point("resolve_company")
    graph.add_edge("resolve_company", "qualification")
    graph.add_conditional_edges(
        "qualification",
        _qualification_route,
        {"continue": "fetch_all", "end": END},
    )
    graph.add_edge("fetch_all", "research")
    graph.add_edge("research", "merge")
    graph.add_edge("merge", "data_quality")
    graph.add_edge("data_quality", "synthesise")
    graph.add_edge("synthesise", "render_persist")
    graph.add_edge("render_persist", END)

    return graph.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────


async def run_pipeline(
    company_name: str,
    domain: str,
    meeting_date: date,
    partner: str,
) -> BriefState:
    """Construct initial state, invoke the graph, return the final state.

    ``ainvoke`` returns a dict view of the final state under LangGraph 1.x.
    We revalidate via :meth:`BriefState.model_validate` so callers always see
    a properly typed model.
    """
    initial = BriefState(
        company_name=company_name,
        domain=domain,
        meeting_date=meeting_date,
        partner=partner,
    )
    compiled = build_graph()
    final = await compiled.ainvoke(initial)
    if isinstance(final, BriefState):
        return final
    return BriefState.model_validate(final)
