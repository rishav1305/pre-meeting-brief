/**
 * PipelineStageCard — expandable per-stage detail card.
 *
 * Server component (no hooks). Expand/collapse is pure CSS via <details>/<summary>
 * so there's zero JS cost for the interactive bit. Click the row → it opens.
 *
 * Visual flavor:
 *   - agentic       → purple-tinted    (LLM call inside this stage)
 *   - deterministic → slate-tinted     (pure Python, no LLM, no MCP)
 *   - mcp           → teal-tinted      (touches an MCP boundary / subprocess)
 *
 * The stage list itself is exported as STAGES so the /pipeline page can
 * iterate it. Each stage's body shows reads/writes/bounds/model/signature so
 * a reviewer can answer "what exactly does this node do" without spelunking.
 */

export type StageFlavor = "agentic" | "deterministic" | "mcp";

export type StageMeta = {
  id: string;
  ordinal: number;
  label: string;
  flavor: StageFlavor;
  oneLiner: string;
  inputs: string[];
  outputs: string[];
  bounds: string;
  model?: string;
  toolUse?: boolean;
  codeSig: string;
};

export const STAGES: StageMeta[] = [
  {
    id: "resolve_company",
    ordinal: 1,
    label: "Resolve company",
    flavor: "deterministic",
    oneLiner:
      "Normalizes the domain, finds-or-creates the canonical company row, opens an etl_run_log row to track this pipeline run.",
    inputs: [
      "state.domain",
      "state.company_name",
      "state.partner",
      "state.meeting_date",
    ],
    outputs: ["state.company_id (UUID)", "state.run_id (UUID)", "state.started_at"],
    bounds: "Pure SQL UPSERT. Idempotent on (domain). No retries needed.",
    codeSig: "async def resolve_company(state: BriefState) -> BriefState",
  },
  {
    id: "qualification",
    ordinal: 2,
    label: "Qualification (agent)",
    flavor: "agentic",
    oneLiner:
      "Decides if this counts as a 'first meeting in rolling 3-month window'. Deterministic 90-day prefilter + LLM judgment for edge cases.",
    inputs: ["state.attio_raw (interactions)", "state.meeting_date"],
    outputs: [
      "state.qualification: 'proceed' | 'skip' | 'flag_for_human'",
      "state.qualification_reason",
    ],
    bounds: "Max 1 LLM call. 30s wallclock. Graceful default: 'proceed' if LLM fails.",
    model: "claude-haiku-4-5",
    toolUse: false,
    codeSig: "async def qualification_agent(state: BriefState) -> BriefState",
  },
  {
    id: "fetch_all",
    ordinal: 3,
    label: "Fetch sources",
    flavor: "mcp",
    oneLiner:
      "Concurrent fetch from 4 providers via asyncio.gather. specter-mcp is a real subprocess MCP roundtrip; crunchbase, pitchbook, attio are in-process providers reading fixtures.",
    inputs: ["state.domain"],
    outputs: [
      "state.specter_raw",
      "state.crunchbase_raw",
      "state.pitchbook_raw",
      "state.attio_raw",
      "state.data_quality_flags (on provider failures)",
    ],
    bounds:
      "asyncio.gather(return_exceptions=True). One source down doesn't fail the brief — failures become DQ flags.",
    codeSig: "async def fetch_all(state: BriefState) -> BriefState",
  },
  {
    id: "research",
    ordinal: 4,
    label: "Research (agent)",
    flavor: "agentic",
    oneLiner:
      "Claude Sonnet 4.6 with the native web_search_20250305 tool. Loops up to 5 search queries, deepens on key findings.",
    inputs: ["state.company_name", "state.domain", "state.specter_raw (for hints)"],
    outputs: ["state.web_raw (markdown summary)", "state.web_citations (URL list)"],
    bounds:
      "Max 5 tool_use calls. 60s wallclock. Max 1500 output tokens. Graceful fallback: empty web_raw, no error raised.",
    model: "claude-sonnet-4-6",
    toolUse: true,
    codeSig: "async def research_agent(state: BriefState) -> BriefState",
  },
  {
    id: "merge",
    ordinal: 5,
    label: "Merge canonical",
    flavor: "deterministic",
    oneLiner:
      "Applies the Data Dictionary's source-priority chains (e.g. total_raised_usd ← COALESCE(PB, S, CB)). Runs 6 conflict detectors. Audit JSONB built per field.",
    inputs: [
      "state.specter_raw",
      "state.crunchbase_raw",
      "state.pitchbook_raw",
      "state.attio_raw",
    ],
    outputs: [
      "state.company_profile",
      "state.team_people",
      "state.traction_signals",
      "state.data_quality_flags",
    ],
    bounds:
      "Pure Python. 6 conflict rules per the DD (founded_year delta, hq_country mismatch, last_round_date delta, operating_status, employee_count 2× CB, g2_rating). Always produces output even when sources are missing — uses what's available.",
    codeSig: "def merge_canonical(state: BriefState) -> BriefState",
  },
  {
    id: "data_quality",
    ordinal: 6,
    label: "Data quality (agent)",
    flavor: "agentic",
    oneLiner:
      "Ranks the conflict flags from merge by severity (high > medium > low) + critical-field priority. Optional Haiku tie-break when ambiguous.",
    inputs: ["state.data_quality_flags"],
    outputs: ["state.dq_ranked"],
    bounds:
      "Rule-based first; LLM invoked only when ≥6 same-severity ambiguous flags AND total >8. Max 1 LLM call. 0s when no flags emitted.",
    model: "claude-haiku-4-5",
    toolUse: false,
    codeSig: "async def data_quality_agent(state: BriefState) -> BriefState",
  },
  {
    id: "synthesise",
    ordinal: 7,
    label: "Synthesise (agent)",
    flavor: "agentic",
    oneLiner:
      "Claude Sonnet 4.6 with FORCED tool_use against the submit_brief schema. Draft → critique → revise. Forced tool_use guarantees valid JSON via SDK schema validation.",
    inputs: [
      "state.company_profile",
      "state.team_people",
      "state.traction_signals",
      "state.attio_raw (engagement history)",
      "state.web_raw",
      "state.dq_ranked",
    ],
    outputs: ["state.brief_json (BriefOutput shape)", "state.brief_html"],
    bounds:
      "Max 3 LLM calls (draft + critique + revise). 240s per call. 540s wallclock budget. Critique and revise failures fall back to draft.",
    model: "claude-sonnet-4-6",
    toolUse: true,
    codeSig: "async def synthesise_brief(state: BriefState) -> BriefState",
  },
  {
    id: "render_persist",
    ordinal: 8,
    label: "Render & persist",
    flavor: "deterministic",
    oneLiner:
      "Writes the final brief into canonical.pre_meeting_brief with 3 frozen audit JSONB columns. Closes etl_run_log with status='complete'.",
    inputs: [
      "state.brief_json",
      "state.brief_html",
      "state.company_profile (for audit)",
    ],
    outputs: ["state.brief_id (UUID, persisted)"],
    bounds:
      "Pure SQL INSERT + UPDATE. On synthesis failure (brief_json is None), marks run as 'failed' without writing a brief row.",
    codeSig: "async def render_and_persist(state: BriefState) -> BriefState",
  },
];

// ─── styling tables (flavor → tailwind class strings) ────────────────────────
const FLAVOR_CARD: Record<StageFlavor, string> = {
  agentic: "border-purple-200 bg-purple-50/40 hover:bg-purple-50/60",
  deterministic: "border-slate-200 bg-slate-50/60 hover:bg-slate-100/60",
  mcp: "border-teal-200 bg-teal-50/40 hover:bg-teal-50/60",
};

const FLAVOR_PILL: Record<StageFlavor, string> = {
  agentic: "bg-purple-100 text-purple-700 ring-1 ring-inset ring-purple-200",
  deterministic: "bg-slate-200 text-slate-700 ring-1 ring-inset ring-slate-300",
  mcp: "bg-teal-100 text-teal-700 ring-1 ring-inset ring-teal-200",
};

const FLAVOR_LABEL: Record<StageFlavor, string> = {
  agentic: "agentic",
  deterministic: "deterministic",
  mcp: "MCP",
};

export function PipelineStageCard({ stage }: { stage: StageMeta }) {
  return (
    <details
      id={`stage-${stage.id}`}
      className={`group rounded-lg border ${FLAVOR_CARD[stage.flavor]} px-5 py-4 transition-colors`}
    >
      <summary className="cursor-pointer list-none">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1.5">
            <span className="font-mono text-xs tabular-nums text-slate-400">
              {String(stage.ordinal).padStart(2, "0")}
            </span>
            <h3 className="text-base font-semibold text-slate-900">{stage.label}</h3>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${FLAVOR_PILL[stage.flavor]}`}
            >
              {FLAVOR_LABEL[stage.flavor]}
            </span>
            {stage.toolUse && (
              <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-indigo-700 ring-1 ring-inset ring-indigo-200">
                tool_use
              </span>
            )}
          </div>
          <span className="shrink-0 whitespace-nowrap text-xs text-slate-400 group-open:hidden">
            Expand ▾
          </span>
          <span className="hidden shrink-0 whitespace-nowrap text-xs text-slate-400 group-open:inline">
            Collapse ▴
          </span>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{stage.oneLiner}</p>
      </summary>

      {/* Expanded body */}
      <div className="mt-4 grid gap-4 border-t border-slate-200 pt-4 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Reads
          </p>
          <ul className="mt-1.5 space-y-1 text-xs text-slate-600">
            {stage.inputs.map((i) => (
              <li key={i}>
                <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[11px] ring-1 ring-inset ring-slate-200">
                  {i}
                </code>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Writes
          </p>
          <ul className="mt-1.5 space-y-1 text-xs text-slate-600">
            {stage.outputs.map((o) => (
              <li key={o}>
                <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[11px] ring-1 ring-inset ring-slate-200">
                  {o}
                </code>
              </li>
            ))}
          </ul>
        </div>
        <div className="sm:col-span-2">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Bounds &amp; failure
          </p>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{stage.bounds}</p>
        </div>
        {stage.model && (
          <div className="sm:col-span-2">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Model
            </p>
            <code className="mt-1.5 inline-block rounded bg-white px-2 py-0.5 font-mono text-[11px] text-slate-700 ring-1 ring-inset ring-slate-200">
              {stage.model}
            </code>
          </div>
        )}
        <div className="sm:col-span-2">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Function signature
          </p>
          <pre className="mt-1.5 overflow-x-auto rounded bg-slate-900 px-3 py-2 font-mono text-[11px] text-slate-100">
            {stage.codeSig}
          </pre>
        </div>
      </div>
    </details>
  );
}
