import Link from "next/link";

import { ArchitectureSvg } from "@/components/ArchitectureSvg";
import { PipelineStageCard, STAGES } from "@/components/PipelineStageCard";
import { SampleRunTrace } from "@/components/SampleRunTrace";

// `searchParams` is dynamic per the App Router; this page reads ?tab=… so it
// can't be force-static anymore. (Sub-trace also hits a live API.)
export const dynamic = "force-dynamic";

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

type TabId = "architecture" | "a-real-run" | "observability" | "design-notes";

const TABS: { id: TabId; label: string }[] = [
  { id: "architecture", label: "Architecture" },
  { id: "a-real-run", label: "A real run" },
  { id: "observability", label: "Observability" },
  { id: "design-notes", label: "Design notes" },
];

function isTab(s: string | undefined): s is TabId {
  return !!s && (TABS as { id: string }[]).some((t) => t.id === s);
}

export default async function PipelinePage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const params = await searchParams;
  const tab: TabId = isTab(params.tab) ? params.tab : "architecture";

  return (
    <main className="px-6 py-10 sm:py-14">
      <div className="mx-auto max-w-5xl">
        <header className="pb-6">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            How it works
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
            Pipeline
          </h1>
          <p className="mt-2 max-w-2xl text-base text-slate-600">
            How a pre-meeting brief gets built &mdash; the agentic system behind the
            agenda. Click any stage card to expand its full contract: inputs, outputs,
            bounds, model, and function signature.
          </p>
        </header>

        {/* Tab strip — server-rendered links, ?tab=… driven */}
        <nav
          className="sticky top-0 z-10 -mx-6 mb-8 border-b border-slate-200 bg-slate-50/95 px-6 py-2 backdrop-blur supports-[backdrop-filter]:bg-slate-50/75"
          aria-label="Pipeline page sections"
        >
          <ul className="flex flex-wrap gap-1">
            {TABS.map((t) => {
              const active = t.id === tab;
              return (
                <li key={t.id}>
                  <Link
                    href={`/pipeline?tab=${t.id}`}
                    scroll={false}
                    className={[
                      "inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium transition",
                      active
                        ? "bg-slate-900 text-white shadow-sm"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                    ].join(" ")}
                    aria-current={active ? "page" : undefined}
                  >
                    {t.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {tab === "architecture" && <ArchitectureTab />}
        {tab === "a-real-run" && <RealRunTab />}
        {tab === "observability" && <ObservabilityTab />}
        {tab === "design-notes" && <DesignNotesTab />}
      </div>
    </main>
  );
}

// ─── tab: Architecture ─────────────────────────────────────────────────────
function ArchitectureTab() {
  return (
    <>
      <section>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
          The diagram
        </h2>
        <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white p-4">
          <ArchitectureSvg />
        </div>
        <p className="mt-3 text-sm italic text-slate-600">
          The agentic layer (purple) replaces the original heuristic DAG. Deterministic
          core (slate) preserves consistency where it matters. Source providers exposed
          via MCP (teal) are pluggable. Every stage below corresponds to one node in
          the LangGraph orchestrator.
        </p>

        {/* Color-key legend */}
        <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-600">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-purple-300" aria-hidden />
            agentic (LLM call)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-400" aria-hidden />
            deterministic (pure Python)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-teal-300" aria-hidden />
            MCP boundary
          </span>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
          Stages
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Eight nodes, executed in order. Click to expand each one for inputs, outputs,
          bounds, model, and function signature.
        </p>
        <div className="mt-6 space-y-3">
          {STAGES.map((stage) => (
            <PipelineStageCard key={stage.id} stage={stage} />
          ))}
        </div>

        <div className="mt-6 rounded-md border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
          <span className="font-medium text-slate-900">Cost discipline.</span>{" "}
          4 of the 8 stages are deterministic Python (free). 2 use Haiku 4.5 (cheap
          tie-break). Only 2 use Sonnet 4.6 — Research (with web_search) and Synthesis
          (with forced tool_use). Brief budget: &lt;$0.20 / &lt;60s end-to-end.
        </div>
      </section>
    </>
  );
}

// ─── tab: A real run ───────────────────────────────────────────────────────
function RealRunTab() {
  return (
    <>
      <section>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
          A real run
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          The static diagram describes the shape of the system. This section grounds it
          in actual data: a pinned completed brief&rsquo;s{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px]">
            node_history
          </code>
          , rendered as a per-stage timeline with real wall-clock durations and the
          message each node logged.
        </p>
      </section>

      <section className="mt-6">
        <SampleRunTrace />
      </section>

      <section className="mt-8 rounded-md border border-slate-200 bg-white px-4 py-3 text-xs leading-relaxed text-slate-600">
        Want to watch a fresh run assemble?{" "}
        <Link
          href="/admin"
          className="font-medium text-slate-900 underline underline-offset-2 hover:text-slate-700"
        >
          /admin
        </Link>{" "}
        triggers a new pipeline run and streams the same per-node timeline live (polls
        every 2 seconds).
      </section>
    </>
  );
}

// ─── tab: Observability ────────────────────────────────────────────────────
function ObservabilityTab() {
  return (
    <section>
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">
        Observability
      </h2>
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-slate-700">
        <p>
          Every run opens a row in{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
            etl_run_log
          </code>{" "}
          with start time, status, latency, the final brief id, and a JSONB{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
            node_history
          </code>{" "}
          array. Each node writes <em>two</em> records into that array — one when it
          starts, one when it finishes — so the live status endpoint can re-derive a
          full timeline (durations, messages, current stage) without a separate events
          table.
        </p>
        <p>
          Conflicts and missing fields land in{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
            data_quality_flags
          </code>{" "}
          keyed to the entity they describe, so the UI surfaces confidence inline
          (the dot on each brief field) rather than hiding it. Click any flag in the
          rendered brief to open the audit panel and see the source-by-source
          provenance for that value.
        </p>
        <p>
          Each agent appends its tool calls (and their inputs/outputs) to a per-run
          audit trail &mdash; useful for debugging hallucinations, replaying a
          failure, and feeding the eval rubric.
        </p>
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <span className="font-semibold">Live now.</span> The{" "}
          <Link
            href="/admin"
            className="font-medium underline underline-offset-2 hover:text-emerald-900"
          >
            /admin
          </Link>{" "}
          page triggers fresh runs, and{" "}
          <Link
            href="/pipeline?tab=a-real-run"
            className="font-medium underline underline-offset-2 hover:text-emerald-900"
          >
            “A real run”
          </Link>{" "}
          replays the pinned reference run&rsquo;s node history.
        </div>
      </div>
    </section>
  );
}

// ─── tab: Design notes ─────────────────────────────────────────────────────
function DesignNotesTab() {
  return (
    <>
      <section>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
          Design notes
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          The reasoning behind the shape of the pipeline &mdash; what we kept agentic,
          what we made deterministic, and why.
        </p>
      </section>

      <section className="mt-6 space-y-5 text-sm leading-relaxed text-slate-700">
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            Why a hybrid (not all-LLM, not all-rules)
          </h3>
          <p className="mt-1">
            The merge step is the consistency contract: <em>this</em> is where the Data
            Dictionary&rsquo;s priority chains and conflict rules live, expressed as
            plain Python. The agentic surface is reserved for the parts that genuinely
            need judgment &mdash; first-meeting qualification, deep-dive web research,
            data-quality tie-breaks, and synthesis. Everything else is deterministic
            Python so it&rsquo;s testable, debuggable, and free.
          </p>
        </div>

        <div>
          <h3 className="text-base font-semibold text-slate-900">
            Why forced tool_use for synthesis
          </h3>
          <p className="mt-1">
            Synthesis is the highest-leverage call and the easiest to get wrong (drift
            into prose, return malformed JSON, hallucinate fields). We invoke Sonnet
            with the{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
              submit_brief
            </code>{" "}
            tool and{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
              tool_choice = required
            </code>
            . The SDK then validates the response against the schema for free &mdash;
            no parse-the-LLM-prose step in the hot path.
          </p>
        </div>

        <div>
          <h3 className="text-base font-semibold text-slate-900">
            Why MCP for source providers
          </h3>
          <p className="mt-1">
            specter-mcp lives in its own process behind the MCP protocol so the
            pipeline can&rsquo;t accidentally reach into provider internals, and so
            we can swap implementations (fixture-backed for the POC, real API for
            prod) by changing the subprocess command, not the calling code. The other
            three providers expose the same{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
              DataProvider
            </code>{" "}
            interface in-process to keep the POC fast.
          </p>
        </div>

        <div>
          <h3 className="text-base font-semibold text-slate-900">
            Why graceful degradation everywhere
          </h3>
          <p className="mt-1">
            A pre-meeting brief is graded on whether the partner can walk into the
            meeting prepared, not on whether every API was up. Each fetch uses{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
              asyncio.gather(return_exceptions=True)
            </code>{" "}
            so one source down doesn&rsquo;t fail the brief. Research falls back to an
            empty <code className="font-mono">web_raw</code>. Synthesis falls back from
            critique → revise to just the draft on any sub-call failure. The whole
            thing is allergic to dropping briefs.
          </p>
        </div>
      </section>

      <section className="mt-10">
        <h3 className="text-base font-semibold text-slate-900">Inline ASCII diagram</h3>
        <p className="mt-1 text-sm text-slate-600">
          The same architecture in monospace &mdash; useful if you&rsquo;re reviewing
          the doc and want the shape of the system in-line with the prose.
        </p>
        <pre className="mt-3 overflow-x-auto rounded bg-slate-900 p-4 text-xs text-slate-100">
          {ASCII_DIAGRAM}
        </pre>
      </section>
    </>
  );
}
