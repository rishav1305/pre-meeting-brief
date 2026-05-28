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
from uuid import UUID

from langgraph.graph import END, StateGraph

from api.pipeline.agents.data_quality import data_quality_agent
from api.pipeline.agents.qualification import qualification_agent
from api.pipeline.agents.research import research_agent
from api.pipeline.agents.synthesis import synthesise_brief
from api.pipeline.merge import merge_canonical
from api.pipeline.nodes import fetch_all, render_and_persist, resolve_company
from api.pipeline.progress import (
    message_for,
    record_node_complete,
    record_node_failed,
    record_node_start,
)
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


def _wrap_node(node_name: str, fn):
    """Wrap a pipeline node with progress recording (start/complete/failed).

    Each node's start/finish writes a record to ``etl_run_log.node_history``
    via :mod:`api.pipeline.progress`. ``record_node_start`` is a no-op when
    ``state.run_id is None`` (i.e. early in resolve_company before the
    run-log row exists), so callers can wrap every node uniformly.
    """
    async def wrapped(state: BriefState) -> BriefState:
        await record_node_start(state.run_id, node_name)
        try:
            result = await fn(state)
            # fn may return a new state object or mutate in place
            final_state = result if result is not None else state
            await record_node_complete(
                final_state.run_id, node_name, message_for(node_name, final_state)
            )
            return final_state
        except Exception as exc:  # noqa: BLE001
            await record_node_failed(
                state.run_id, node_name, f"{type(exc).__name__}: {exc}"
            )
            raise

    return wrapped


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

    graph.add_node("resolve_company", _wrap_node("resolve_company", resolve_company))
    graph.add_node("qualification", _wrap_node("qualification", qualification_agent))
    graph.add_node("fetch_all", _wrap_node("fetch_all", fetch_all))
    graph.add_node("research", _wrap_node("research", research_agent))
    graph.add_node("merge", _wrap_node("merge", _merge_node))
    graph.add_node("data_quality", _wrap_node("data_quality", data_quality_agent))
    graph.add_node("synthesise", _wrap_node("synthesise", synthesise_brief))
    graph.add_node("render_persist", _wrap_node("render_persist", render_and_persist))

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
    run_id: UUID | None = None,
) -> BriefState:
    """Construct initial state, invoke the graph, return the final state.

    ``ainvoke`` returns a dict view of the final state under LangGraph 1.x.
    We revalidate via :meth:`BriefState.model_validate` so callers always see
    a properly typed model.

    ``run_id`` (optional): when the caller has already created an
    ``etl_run_log`` row up front (e.g. the admin trigger endpoint, so the HTTP
    response can include the run_id before the pipeline finishes),
    pass it here. :func:`resolve_company` will reuse that row instead of
    opening a new one.
    """
    initial = BriefState(
        company_name=company_name,
        domain=domain,
        meeting_date=meeting_date,
        partner=partner,
        run_id=run_id,
    )
    compiled = build_graph()
    final = await compiled.ainvoke(initial)
    if isinstance(final, BriefState):
        return final
    return BriefState.model_validate(final)
