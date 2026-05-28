"use client";
import { useEffect, useState } from "react";
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

const NODE_LABELS: Record<string, string> = {
  resolve_company: "Resolve company",
  qualification: "Qualification (agent)",
  fetch_all: "Fetch sources",
  research: "Research (agent)",
  merge: "Merge canonical",
  data_quality: "Data quality (agent)",
  synthesise: "Synthesise (agent)",
  render_persist: "Render & persist",
};
const NODE_ORDER = [
  "resolve_company", "qualification", "fetch_all", "research",
  "merge", "data_quality", "synthesise", "render_persist",
];

export function RunStatus({ runId, onReset }: { runId: string; onReset: () => void }) {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch(`/pre-meeting-brief/api/triggers/runs/${runId}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) setStatus(data);
        if (data.status === "running") {
          setTimeout(poll, 2000);
        }
      } catch {
        if (!cancelled) setTimeout(poll, 3000);
      }
    }
    poll();
    return () => { cancelled = true; };
  }, [runId]);

  const isRunning = status?.status === "running" || !status;
  const isFailed = status?.status === "failed";
  const isComplete = status?.status === "complete";

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Run</p>
        <p className="mt-1 font-mono text-xs text-slate-700">{runId}</p>
        <p className="mt-2 text-sm text-slate-600">
          Status: {" "}
          <span className={
            isComplete ? "font-semibold text-emerald-700" :
            isFailed ? "font-semibold text-rose-700" :
            "font-semibold text-slate-700"
          }>
            {status?.status ?? "starting…"}
          </span>
        </p>
      </div>

      <ol className="space-y-2 border-l-2 border-slate-200 pl-4">
        {NODE_ORDER.map((node, idx) => {
          // For Phase 2, we can't yet introspect per-node progress through the endpoint
          // (Phase 3 adds tool_calls table). Approximate: all nodes are "running" during
          // run, "complete" when finished, "failed" if failed.
          let symbol = "○";
          let cls = "text-slate-300";
          if (isComplete) { symbol = "●"; cls = "text-emerald-600"; }
          else if (isFailed) { symbol = "✗"; cls = "text-rose-600"; }
          else if (isRunning && idx === 0) { symbol = "◐"; cls = "text-amber-600"; }
          return (
            <li key={node} className="flex items-start gap-3 text-sm">
              <span className={`font-mono ${cls}`}>{symbol}</span>
              <span className="text-slate-700">{NODE_LABELS[node]}</span>
            </li>
          );
        })}
      </ol>

      {isComplete && status?.brief_id && (
        <Link
          href={`/briefs/${status.brief_id}`}
          className="inline-block rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          View brief →
        </Link>
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
    </div>
  );
}
