import { ArchitectureSvg } from "@/components/ArchitectureSvg";

export const dynamic = "force-static";

const ASCII_DIAGRAM = `                  ┌──────────────────────────────────────┐
                  │  TRIGGERS                            │
                  │  • Vercel Cron (daily 06:00 UTC)     │
                  │  • Manual button (admin UI)          │
                  └──────────────────────────────────────┘
                                  │
                                  ▼
                  ┌──────────────────────────────────────┐
                  │  Qualification Agent  [agentic]      │
                  │  - Is this really a "first meeting"  │
                  │    per the rolling 3-month rule?     │
                  │  - Handles edge cases (conferences,  │
                  │    prior intros, etc.)               │
                  │  - Decides: proceed | skip | flag    │
                  └──────────────────────────────────────┘
                                  │ proceed
                                  ▼
                  ┌──────────────────────────────────────┐
                  │  resolve_company  [deterministic]    │
                  │  - Normalize domain                  │
                  │  - Upsert canonical.company          │
                  │  - Open etl_run_log row              │
                  └──────────────────────────────────────┘
                                  │
                                  ▼
                  ┌──────────────────────────────────────┐
                  │  Orchestrator (LangGraph)            │
                  │  State: BriefState (pydantic)        │
                  └──────────────────────────────────────┘
                                  │
       ┌──────────────┬───────────┴───────────┬──────────────┐
       ▼              ▼                       ▼              ▼
   Research      Source-fetch fan-out     DQ Agent      Synthesis
   Agent         [deterministic+MCP]      [agentic]     Agent
   [agentic]                                            [agentic]
   ↓ tools       ↓ MCP clients            ↓ tools       ↓ tools
   ┌─────────┐   ┌──────────────┐         ┌──────────┐  ┌────────────┐
   │ web     │   │ specter-mcp  │         │ get      │  │ get        │
   │ search  │   │ crunchbase-  │         │ canonical│  │ canonical  │
   │ (real   │   │   mcp        │         │ context  │  │ context    │
   │ Anthr.) │   │ pitchbook-   │         │ get      │  │ critique-  │
   │ loop:   │   │   mcp        │         │ flags    │  │ self-      │
   │ deep    │   │ attio-mcp    │         │ rank by  │  │ revise loop│
   │ dive    │   │ (fixture     │         │ severity │  │            │
   │ on key  │   │  backed for  │         │          │  │            │
   │ finds   │   │  POC)        │         │          │  │            │
   └─────────┘   └──────────────┘         └──────────┘  └────────────┘
                          │
                          ▼
              ┌──────────────────────────────────────┐
              │  merge_canonical  [deterministic]    │
              │  - COALESCE priority chains per DD   │
              │  - Conflict detection                │
              │  - Emit data_quality_flags           │
              │  - Write audit VARIANT per entity    │
              └──────────────────────────────────────┘
                          │
                          ▼
              ┌──────────────────────────────────────┐
              │  Render & Persist  [deterministic]   │
              │  - Compose final brief JSON          │
              │  - Write canonical.pre_meeting_brief │
              │  - Close etl_run_log                 │
              │  - HTML page renders from JSON       │
              │  - Print stylesheet substitutes PDF  │
              └──────────────────────────────────────┘
                          │
                          ▼
              ┌──────────────────────────────────────┐
              │  DISTRIBUTION                        │
              │  • Daily Agenda page lists brief     │
              │  • Stable URL (versioned)            │
              │  • [stub] Attio writeback (would     │
              │    push folder link to CRM record)   │
              └──────────────────────────────────────┘

  ──────────────────────────────────────────────────────────
  Cross-cutting layers:

  Observability:    etl_run_log + data_quality_flags + agent
                    tool-call audit trail
  Idempotency:      version-pinned briefs, refresh-on-demand
  Cost discipline:  Sonnet (synthesis), Haiku (cheap ops),
                    bounded agent loops
  Auth (POC):       Public read; admin trigger password-gated
  Auth (prod):      Firm SSO, partner-cohort scoping
  Secrets:          Vercel env (POC); Vault/Secrets Mgr (prod)
  Eval (stretch):   Haiku-scored rubric on 5 axes, golden set
`;

export default function PipelinePage() {
  return (
    <main className="px-6 py-10 sm:py-14">
      <div className="mx-auto max-w-5xl">
        <header className="pb-6">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            How it works
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">Pipeline</h1>
          <p className="mt-2 max-w-2xl text-base text-slate-600">
            How a pre-meeting brief gets built &mdash; the agentic system behind the agenda.
          </p>
        </header>

        <section className="mt-10">
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Architecture</h2>
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white p-4">
            <ArchitectureSvg />
          </div>
          <p className="mt-3 text-sm italic text-slate-600">
            Corrected v2 architecture. The agentic layer (purple) replaces the original heuristic
            DAG. Deterministic core (slate) preserves consistency where it matters. Source
            providers exposed via MCP (teal) are pluggable.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Stage by stage</h2>

          <div className="mt-6 space-y-6 text-sm leading-relaxed text-slate-700">
            <div>
              <h3 className="text-base font-semibold text-slate-900">1. Trigger</h3>
              <p className="mt-1">
                Vercel Cron daily plus a manual <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">/admin</code>{" "}
                button. Phase 2 routes both through the Qualification Agent so the &ldquo;is this
                really a first meeting?&rdquo; logic lives in one place instead of duplicated at the
                edges.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900">2. Qualification</h3>
              <p className="mt-1">
                Agent decides if this counts as a first meeting in the rolling 3-month window. It
                handles the edge cases the original heuristic DAG papers over &mdash; conference
                encounters last month, prior partner intros, dormant relationships that re-open,
                etc. Output is one of <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">proceed</code>,{" "}
                <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">skip</code>, or{" "}
                <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">flag</code>.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900">3. Source fetch (parallel)</h3>
              <p className="mt-1">
                Research Agent loops <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">web_search</code>{" "}
                for the unstructured story. Four MCP / in-process providers
                (Specter, Crunchbase, PitchBook, Attio) fetch from fixtures in the POC and real
                APIs in production. One source down doesn&rsquo;t fail the brief &mdash;
                failures become <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">data_quality_flags</code>{" "}
                surfaced to the partner instead of a 500.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900">4. Merge</h3>
              <p className="mt-1">
                Deterministic Python applies the Data Dictionary&rsquo;s source-priority chains
                &mdash; e.g.{" "}
                <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">
                  total_raised_usd &larr; COALESCE(PitchBook, Specter, Crunchbase)
                </code>
                . Six conflict detectors run across the merged record and emit DQ flags when
                providers disagree materially. The audit JSONB is frozen at brief-generation time
                so every value remains traceable to its source even after upstream APIs change.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900">5. Synthesis</h3>
              <p className="mt-1">
                Claude Sonnet 4.6 with a Renegade-thesis-tuned system prompt. The loop is{" "}
                <em>draft &rarr; critique &rarr; revise</em>, bounded at 3 iterations or 90 seconds
                of wall time. Output is strict JSON conforming to{" "}
                <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">BriefOutput</code> so the
                renderer is dumb &mdash; no parse-the-LLM-prose step in the hot path.
              </p>
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900">6. Render &amp; distribute</h3>
              <p className="mt-1">
                HTML is rendered server-side from the JSON, persisted to{" "}
                <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">pre_meeting_brief</code>,
                and surfaced on the agenda with a stable versioned URL. In production this also
                writes back to the Attio CRM record and posts a morning digest to Slack so the
                partner sees today&rsquo;s briefs without opening the app.
              </p>
            </div>
          </div>
        </section>

        <section className="mt-12">
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Observability</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-700">
            Every run opens a row in <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">etl_run_log</code>{" "}
            with start time, status, latency, token spend, and the final brief id. Conflicts and
            missing fields land in{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">data_quality_flags</code>{" "}
            keyed to the entity they describe, so the UI can surface confidence inline rather than
            hiding it. Each agent appends its tool calls (and their inputs/outputs) to a per-run
            audit trail &mdash; useful for debugging hallucinations and for the eval rubric. Phase 2
            will surface live runs on this page so you can watch a brief assemble.
          </p>
        </section>

        <section className="mt-12">
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Live run traces, real LLM synthesis, and admin trigger ship in Phase 2 (the next plan).
            This page is the static architecture preview.
          </div>
        </section>

        <section className="mt-12">
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Inline ASCII diagram
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            The same architecture in monospace &mdash; useful when you&rsquo;re reviewing the doc
            and want the diagram in-line with the prose.
          </p>
          <pre className="mt-4 overflow-x-auto rounded bg-slate-900 p-4 text-xs text-slate-100">
            {ASCII_DIAGRAM}
          </pre>
        </section>

      </div>
    </main>
  );
}
