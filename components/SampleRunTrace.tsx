/**
 * SampleRunTrace — server component.
 *
 * Loads a known-good completed pipeline run from the triggers API and renders
 * its `node_history` as a real per-stage timeline. This grounds the abstract
 * architecture in concrete data — you can see actual durations and messages
 * from an end-to-end run.
 *
 * If the fetch fails (network, deployment not up, run pruned, etc.) the
 * component falls back to a graceful "trace unavailable" panel rather than
 * blowing up the page.
 *
 * The run_id is hardcoded for now — see SAMPLE_RUN_ID. We pick a recently-known
 * completed brief's run so the durations are representative.
 */

// Hardcoded for the demo. If this run is ever GC'd, the component falls back
// to the unavailable-state panel below — no crash.
const SAMPLE_RUN_ID = "415357c5-3cae-455e-ade6-dd372724d8ce";

type NodeStatus = "running" | "complete" | "failed";

type NodeHistoryEntry = {
  node: string;
  status: NodeStatus;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  message: string;
};

type RunStatusResponse = {
  run_id: string;
  status: "running" | "complete" | "failed";
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  company_id: string | null;
  brief_id: string | null;
  current_node: string | null;
  node_history: NodeHistoryEntry[];
  recent_tool_calls: unknown[];
};

// Same resolver as lib/api.ts but locally inlined so this file stays self-
// contained. In server components, fetch needs an absolute URL.
function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window === "undefined") {
    const host = process.env.VERCEL_PROJECT_PRODUCTION_URL ?? process.env.VERCEL_URL;
    if (host) return `https://${host}/api`;
  }
  return "/pre-meeting-brief/api";
}

async function fetchSampleRun(): Promise<RunStatusResponse | null> {
  const base = resolveApiBase();
  try {
    const res = await fetch(`${base}/triggers/runs/${SAMPLE_RUN_ID}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as RunStatusResponse;
  } catch {
    return null;
  }
}

function fmtDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  return `${m}m ${rem.toString().padStart(2, "0")}s`;
}

function fmtTotal(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt || !completedAt) return "—";
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  return fmtDuration(ms);
}

const NODE_LABELS: Record<string, string> = {
  resolve_company: "Resolve company",
  qualification: "Qualification",
  fetch_all: "Fetch sources",
  research: "Research",
  merge: "Merge canonical",
  data_quality: "Data quality",
  synthesise: "Synthesise",
  render_persist: "Render & persist",
};

const AGENTIC_NODES = new Set(["qualification", "research", "data_quality", "synthesise"]);

function nodeLabel(id: string): string {
  return NODE_LABELS[id] ?? id;
}

export async function SampleRunTrace() {
  const run = await fetchSampleRun();

  if (!run || run.node_history.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white px-5 py-4">
        <p className="text-sm font-semibold text-slate-900">
          Live trace unavailable
        </p>
        <p className="mt-2 text-xs leading-relaxed text-slate-600">
          This section normally displays the <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px]">node_history</code>{" "}
          from a real completed pipeline run, so you can see actual per-stage
          durations and messages. The pinned reference run (
          <code className="font-mono text-[11px] text-slate-500">{SAMPLE_RUN_ID.slice(0, 8)}…</code>
          ) couldn&rsquo;t be loaded right now — either the deployment isn&rsquo;t
          reachable from this build, or the run row was pruned. See the static
          architecture diagram above; or trigger a fresh run from{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px]">/admin</code>{" "}
          and watch it live.
        </p>
      </div>
    );
  }

  // Build a max-duration so we can scale bars relative to the longest stage.
  const maxDurationMs = Math.max(
    1,
    ...run.node_history.map((e) => e.duration_ms ?? 0),
  );

  const totalLabel = fmtTotal(run.started_at, run.completed_at);
  const startedStr = run.started_at
    ? new Date(run.started_at).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "unknown";

  const statusColor =
    run.status === "complete"
      ? "text-emerald-700"
      : run.status === "failed"
        ? "text-rose-700"
        : "text-amber-600";

  return (
    <div className="space-y-4">
      {/* Header strip */}
      <div className="rounded-lg border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Run
            </p>
            <p className="mt-1 font-mono text-xs text-slate-600">
              {run.run_id.slice(0, 8)}…
            </p>
            <p className="mt-1 text-xs text-slate-500">Started {startedStr}</p>
          </div>
          <div className="text-right">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Status
            </p>
            <p className={`mt-1 text-sm font-semibold ${statusColor}`}>
              {run.status[0].toUpperCase() + run.status.slice(1)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Total{" "}
              <span className="font-mono tabular-nums text-slate-700">
                {totalLabel}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Per-stage timeline */}
      <ol className="space-y-2">
        {run.node_history.map((entry, idx) => {
          const dur = entry.duration_ms ?? 0;
          const widthPct = Math.max(2, Math.round((dur / maxDurationMs) * 100));
          const isAgentic = AGENTIC_NODES.has(entry.node);
          const barColor =
            entry.status === "failed"
              ? "bg-rose-400"
              : entry.status === "running"
                ? "bg-amber-400"
                : isAgentic
                  ? "bg-purple-400"
                  : "bg-slate-400";
          const symbol =
            entry.status === "complete"
              ? "●"
              : entry.status === "failed"
                ? "✗"
                : "◐";
          const symbolColor =
            entry.status === "complete"
              ? "text-emerald-600"
              : entry.status === "failed"
                ? "text-rose-600"
                : "text-amber-500";

          return (
            <li
              key={`${entry.node}-${idx}`}
              className="rounded-md border border-slate-200 bg-white px-4 py-3"
            >
              <div className="flex items-baseline justify-between gap-3">
                <div className="flex items-baseline gap-2">
                  <span
                    className={`font-mono text-sm ${symbolColor}`}
                    aria-hidden
                  >
                    {symbol}
                  </span>
                  <span className="text-sm font-medium text-slate-900">
                    {nodeLabel(entry.node)}
                  </span>
                  {isAgentic && (
                    <span className="rounded-full bg-purple-100 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-purple-700">
                      agentic
                    </span>
                  )}
                </div>
                <span className="font-mono tabular-nums text-xs text-slate-600">
                  {fmtDuration(entry.duration_ms)}
                </span>
              </div>
              {/* Bar */}
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full ${barColor}`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
              {entry.message && (
                <p className="mt-2 text-xs leading-relaxed text-slate-600">
                  <span className="mr-1 font-mono text-slate-400">→</span>
                  {entry.message}
                </p>
              )}
            </li>
          );
        })}
      </ol>

      <p className="text-xs leading-relaxed text-slate-500">
        <span aria-hidden className="mr-1">ⓘ</span>
        Reading from <code className="font-mono">etl_run_log.node_history</code>{" "}
        for run <code className="font-mono">{run.run_id.slice(0, 8)}…</code>.
        Bar widths are scaled to the longest stage in this run. Total wall time
        is end-to-end (start → complete).
      </p>
    </div>
  );
}
