"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type Status = {
  run_id: string;
  status: "running" | "complete" | "failed";
  started_at?: string;
  completed_at?: string | null;
  error_message?: string | null;
  company_id?: string | null;
  brief_id?: string | null;
};

// Typical wallclock budget per node, in seconds. Used to drive the simulated
// progression bar while a run is in flight (since the status endpoint only
// reports overall status, not per-node). Numbers come from live timings on
// the LiteLLM proxy:
//   resolve_company  ~ 5s
//   qualification    ~ 1s
//   fetch_all        ~ 1s   (4 providers concurrent; bottleneck is the MCP subprocess)
//   research         ~ 45s  (Claude web_search loop, up to 5 queries)
//   merge            ~ 0s   (pure Python)
//   data_quality     ~ 0s
//   synthesise       ~ 120s (Sonnet + forced tool_use)
//   render_persist   ~ 3s
const NODE_TIMINGS: { id: string; label: string; budgetS: number }[] = [
  { id: "resolve_company", label: "Resolve company", budgetS: 5 },
  { id: "qualification", label: "Qualification (agent)", budgetS: 1 },
  { id: "fetch_all", label: "Fetch sources", budgetS: 1 },
  { id: "research", label: "Research (agent)", budgetS: 45 },
  { id: "merge", label: "Merge canonical", budgetS: 1 },
  { id: "data_quality", label: "Data quality (agent)", budgetS: 1 },
  { id: "synthesise", label: "Synthesise (agent)", budgetS: 120 },
  { id: "render_persist", label: "Render & persist", budgetS: 3 },
];

const TOTAL_BUDGET_S = NODE_TIMINGS.reduce((a, n) => a + n.budgetS, 0);

function fmtElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

export function RunStatus({ runId, onReset }: { runId: string; onReset: () => void }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());

  // Poll the status endpoint
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch(`/pre-meeting-brief/api/triggers/runs/${runId}`, {
          cache: "no-store",
        });
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) setStatus(data);
        if (data.status === "running") {
          setTimeout(poll, 2500);
        }
      } catch {
        if (!cancelled) setTimeout(poll, 3000);
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Tick a clock every 500ms so the elapsed counter advances smoothly
  useEffect(() => {
    if (status?.status !== "running" && status !== null) return;
    const interval = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(interval);
  }, [status?.status, status]);

  const startedAtMs = useMemo(() => {
    if (!status?.started_at) return null;
    return new Date(status.started_at).getTime();
  }, [status?.started_at]);

  const elapsedS = startedAtMs ? (now - startedAtMs) / 1000 : 0;

  const isRunning = status?.status === "running" || !status;
  const isFailed = status?.status === "failed";
  const isComplete = status?.status === "complete";

  // Simulated per-node progression: pick which node we're "currently on"
  // based on cumulative budget vs elapsed time. When the actual run finishes
  // before our simulation, we snap everything to complete.
  const currentNodeIndex = useMemo(() => {
    if (isComplete) return NODE_TIMINGS.length;
    if (isFailed || !startedAtMs) return 0;
    let cum = 0;
    for (let i = 0; i < NODE_TIMINGS.length; i++) {
      cum += NODE_TIMINGS[i].budgetS;
      if (elapsedS < cum) return i;
    }
    // Past the typical envelope but still running — show the last node as in-flight
    return NODE_TIMINGS.length - 1;
  }, [elapsedS, isComplete, isFailed, startedAtMs]);

  const pctProgress = useMemo(() => {
    if (isComplete) return 100;
    if (isFailed) return 0;
    return Math.min(98, Math.round((elapsedS / TOTAL_BUDGET_S) * 100));
  }, [elapsedS, isComplete, isFailed]);

  return (
    <div className="space-y-6">
      {/* Header strip */}
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Run</p>
          <p className="mt-1 font-mono text-xs text-slate-500">{runId.slice(0, 8)}…</p>
        </div>
        <div className="text-right">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Status</p>
          <p
            className={`mt-1 text-sm font-semibold ${
              isComplete
                ? "text-emerald-700"
                : isFailed
                  ? "text-rose-700"
                  : "text-amber-600"
            }`}
          >
            {isComplete ? "Complete" : isFailed ? "Failed" : "Running"}
            {isRunning && status && (
              <span className="ml-2 inline-block animate-pulse">●</span>
            )}
          </p>
        </div>
      </div>

      {/* Elapsed + progress bar */}
      <div>
        <div className="flex items-baseline justify-between text-xs text-slate-500">
          <span>
            Elapsed{" "}
            <span className="font-mono tabular-nums text-slate-700">{fmtElapsed(elapsedS)}</span>
            {!isComplete && !isFailed && (
              <span className="ml-2 text-slate-400">
                · expected ~{Math.floor(TOTAL_BUDGET_S / 60)}m{TOTAL_BUDGET_S % 60}s
              </span>
            )}
          </span>
          <span className="font-mono tabular-nums text-slate-500">{pctProgress}%</span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full transition-all duration-500 ${
              isComplete
                ? "bg-emerald-500"
                : isFailed
                  ? "bg-rose-500"
                  : "bg-slate-700"
            }`}
            style={{ width: `${pctProgress}%` }}
          />
        </div>
      </div>

      {/* Per-node timeline */}
      <ol className="space-y-2 border-l-2 border-slate-200 pl-4">
        {NODE_TIMINGS.map((node, idx) => {
          // Decide visual state per node
          let symbol = "○";
          let cls = "text-slate-300";
          let labelCls = "text-slate-500";
          if (isComplete) {
            symbol = "●";
            cls = "text-emerald-600";
            labelCls = "text-slate-700";
          } else if (isFailed) {
            // Mark the last "running" node as failed; earlier nodes look complete
            if (idx < currentNodeIndex) {
              symbol = "●";
              cls = "text-emerald-600";
              labelCls = "text-slate-700";
            } else if (idx === currentNodeIndex) {
              symbol = "✗";
              cls = "text-rose-600";
              labelCls = "text-slate-700";
            }
          } else if (isRunning) {
            if (idx < currentNodeIndex) {
              symbol = "●";
              cls = "text-emerald-600";
              labelCls = "text-slate-700";
            } else if (idx === currentNodeIndex) {
              symbol = "◐";
              cls = "text-amber-600";
              labelCls = "font-medium text-slate-900";
            }
          }
          return (
            <li key={node.id} className="flex items-start gap-3 text-sm">
              <span
                className={`font-mono ${cls} ${idx === currentNodeIndex && isRunning ? "animate-pulse" : ""}`}
              >
                {symbol}
              </span>
              <span className={labelCls}>{node.label}</span>
              {idx === currentNodeIndex && isRunning && (
                <span className="ml-auto text-xs text-slate-400">
                  ~{node.budgetS}s budget
                </span>
              )}
            </li>
          );
        })}
      </ol>

      {/* Outcome */}
      {isComplete && status?.brief_id && (
        <div className="space-y-2">
          <Link
            href={`/briefs/${status.brief_id}`}
            className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700"
          >
            View brief
            <span aria-hidden>→</span>
          </Link>
          <p className="text-xs text-slate-500">
            Brief generated in {fmtElapsed(elapsedS)}.
          </p>
        </div>
      )}
      {isFailed && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {status?.error_message ?? "Pipeline failed."}
        </div>
      )}

      <button
        onClick={onReset}
        className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-700"
      >
        ← Start another
      </button>

      {isRunning && (
        <p className="text-xs text-slate-400">
          Per-node timings above are the typical budget envelope, not the live trace
          (Phase 3 will expose tool-call events for true real-time visibility). The
          actual pipeline IS running on Vercel — refresh to break out.
        </p>
      )}
    </div>
  );
}
