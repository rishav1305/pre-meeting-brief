"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

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
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  company_id: string | null;
  brief_id: string | null;
  current_node: string | null;
  node_history: NodeHistoryEntry[];
  recent_tool_calls: unknown[];
};

type NodeMeta = {
  id: string;
  ordinal: number;
  label: string;
  flavor: "agentic" | "deterministic";
  description: string;
};

const NODE_META: NodeMeta[] = [
  {
    id: "resolve_company",
    ordinal: 1,
    label: "Resolve company",
    flavor: "deterministic",
    description:
      "Normalizes the domain, finds-or-creates the canonical company row, opens an etl_run_log row.",
  },
  {
    id: "qualification",
    ordinal: 2,
    label: "Qualification (agent)",
    flavor: "agentic",
    description:
      "Hybrid: deterministic 90-day prefilter on engagement history + LLM (Haiku) judgment for edge cases (founder at conference, etc.).",
  },
  {
    id: "fetch_all",
    ordinal: 3,
    label: "Fetch sources",
    flavor: "deterministic",
    description:
      "4 providers in parallel via asyncio.gather. specter-mcp is a real subprocess MCP call; crunchbase, pitchbook, attio are in-process providers reading fixtures.",
  },
  {
    id: "research",
    ordinal: 4,
    label: "Research (agent)",
    flavor: "agentic",
    description:
      "Claude Sonnet 4.6 with the native web_search_20250305 tool. Loops up to 5 search queries, deepens on key findings (new funding rounds, exec changes, recent news).",
  },
  {
    id: "merge",
    ordinal: 5,
    label: "Merge canonical",
    flavor: "deterministic",
    description:
      "Applies the Data Dictionary's source-priority chains (e.g. total_raised_usd ← COALESCE(PB, S, CB)) and runs 6 conflict detectors. Audit JSONB built per field.",
  },
  {
    id: "data_quality",
    ordinal: 6,
    label: "Data quality (agent)",
    flavor: "agentic",
    description:
      "Ranks the conflict flags from merge by severity (high > medium > low) + critical-field priority. Optional Haiku tie-break when ambiguous.",
  },
  {
    id: "synthesise",
    ordinal: 7,
    label: "Synthesise (agent)",
    flavor: "agentic",
    description:
      "Claude Sonnet 4.6 with forced tool_use against the submit_brief schema (guaranteed valid JSON). Draft → critique → revise, max 3 iterations.",
  },
  {
    id: "render_persist",
    ordinal: 8,
    label: "Render & persist",
    flavor: "deterministic",
    description:
      "Writes the final brief into canonical.pre_meeting_brief, closes etl_run_log with status='complete'.",
  },
];

function fmtElapsed(seconds: number): string {
  if (seconds < 0) seconds = 0;
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function fmtDuration(ms: number | null): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  return `${m}m ${rem.toString().padStart(2, "0")}s`;
}

export function RunStatus({ runId, onReset }: { runId: string; onReset: () => void }) {
  const [status, setStatus] = useState<RunStatusResponse | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());

  // Poll the status endpoint every 2s while running, stop on terminal status.
  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      try {
        const res = await fetch(`/pre-meeting-brief/api/triggers/runs/${runId}`, {
          cache: "no-store",
        });
        if (!res.ok) {
          if (!cancelled) timeoutId = setTimeout(poll, 2000);
          return;
        }
        const data = (await res.json()) as RunStatusResponse;
        if (cancelled) return;
        setStatus(data);
        if (data.status === "running") {
          timeoutId = setTimeout(poll, 2000);
        }
      } catch {
        if (!cancelled) timeoutId = setTimeout(poll, 2000);
      }
    }
    poll();
    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [runId]);

  // Tick a clock every 500ms while running so elapsed counters advance smoothly.
  useEffect(() => {
    if (status && status.status !== "running") return;
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

  // Index node_history by node id so cards can look themselves up.
  const historyById = useMemo(() => {
    const map = new Map<string, NodeHistoryEntry>();
    if (status?.node_history) {
      for (const entry of status.node_history) {
        // Last write wins (chronological). If a node appears twice (running then
        // complete), the final state is what we want.
        map.set(entry.node, entry);
      }
    }
    return map;
  }, [status?.node_history]);

  const completedCount = useMemo(() => {
    let n = 0;
    for (const meta of NODE_META) {
      const h = historyById.get(meta.id);
      if (h && h.status === "complete") n += 1;
    }
    return n;
  }, [historyById]);

  const runningCount = useMemo(() => {
    let n = 0;
    for (const meta of NODE_META) {
      const h = historyById.get(meta.id);
      if (h && h.status === "running") n += 1;
    }
    return n;
  }, [historyById]);

  const pctProgress = useMemo(() => {
    if (isComplete) return 100;
    if (isFailed) {
      return Math.round((completedCount / NODE_META.length) * 100);
    }
    const fractional = completedCount + 0.5 * runningCount;
    return Math.min(98, Math.round((fractional / NODE_META.length) * 100));
  }, [isComplete, isFailed, completedCount, runningCount]);

  const statusLabel = isComplete ? "Complete" : isFailed ? "Failed" : "Running";
  const statusColor = isComplete
    ? "text-emerald-700"
    : isFailed
      ? "text-rose-700"
      : "text-amber-600";

  return (
    <div className="space-y-6">
      {/* Header strip */}
      <div className="rounded-lg border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Run
            </p>
            <p className="mt-1 font-mono text-xs text-slate-500">{runId.slice(0, 8)}…</p>
          </div>
          <div className="text-right">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Status
            </p>
            <p className={`mt-1 text-sm font-semibold ${statusColor}`}>
              {statusLabel}
              {isRunning && status && (
                <span className="ml-2 inline-block animate-pulse">●</span>
              )}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Elapsed{" "}
              <span className="font-mono tabular-nums text-slate-700">
                {fmtElapsed(elapsedS)}
              </span>
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="flex items-baseline justify-between text-xs text-slate-500">
            <span>
              {completedCount} / {NODE_META.length} stages complete
            </span>
            <span className="font-mono tabular-nums text-slate-500">
              {pctProgress}%
            </span>
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
      </div>

      {/* Section heading */}
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
          Pipeline stages
        </p>
      </div>

      {/* Per-node cards */}
      <ol className="space-y-3">
        {NODE_META.map((meta) => {
          const entry = historyById.get(meta.id);
          const cardStatus: NodeStatus | "pending" = entry?.status ?? "pending";
          const isCurrent = cardStatus === "running";

          let badgeText: string;
          let badgeColor: string;
          let symbol: string;
          let symbolPulse = false;

          if (cardStatus === "pending") {
            badgeText = "Pending";
            badgeColor = "text-slate-400";
            symbol = "○";
          } else if (cardStatus === "running") {
            const runningForS = entry
              ? (now - new Date(entry.started_at).getTime()) / 1000
              : 0;
            badgeText = `Running · ${fmtElapsed(runningForS)}`;
            badgeColor = "text-amber-600";
            symbol = "◐";
            symbolPulse = true;
          } else if (cardStatus === "complete") {
            badgeText = `Complete · ${fmtDuration(entry?.duration_ms ?? null)}`;
            badgeColor = "text-emerald-700";
            symbol = "●";
          } else {
            // failed
            badgeText = "Failed";
            badgeColor = "text-rose-700";
            symbol = "✗";
          }

          const flavorBadge =
            meta.flavor === "agentic" ? (
              <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-indigo-700 ring-1 ring-inset ring-indigo-200">
                Agentic
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-slate-600 ring-1 ring-inset ring-slate-200">
                Deterministic
              </span>
            );

          const cardClasses = [
            "rounded-lg border bg-white px-5 py-4 shadow-sm transition-all",
            isCurrent
              ? "border-amber-200 ring-2 ring-amber-300/40"
              : cardStatus === "failed"
                ? "border-rose-200"
                : cardStatus === "complete"
                  ? "border-slate-200"
                  : "border-slate-200 opacity-70",
          ].join(" ");

          return (
            <li key={meta.id} className={cardClasses}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-baseline gap-3">
                  <span
                    className={`font-mono text-base ${badgeColor} ${
                      symbolPulse ? "animate-pulse" : ""
                    }`}
                    aria-hidden
                  >
                    {symbol}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono tabular-nums text-slate-400">
                        {meta.ordinal}.
                      </span>
                      <span className="text-sm font-semibold text-slate-900">
                        {meta.label}
                      </span>
                      {flavorBadge}
                    </div>
                  </div>
                </div>
                <span
                  className={`shrink-0 whitespace-nowrap text-xs font-semibold ${badgeColor}`}
                >
                  {badgeText}
                </span>
              </div>

              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                {meta.description}
              </p>

              {entry?.message && cardStatus !== "pending" && (
                <p
                  className={`mt-2 text-xs leading-relaxed ${
                    cardStatus === "failed"
                      ? "text-rose-700"
                      : cardStatus === "complete"
                        ? "text-emerald-800"
                        : "text-amber-700"
                  }`}
                >
                  <span className="mr-1 font-mono text-slate-400">→</span>
                  {entry.message}
                </p>
              )}
            </li>
          );
        })}
      </ol>

      {/* Outcome / failure block */}
      {isComplete && status?.brief_id && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-5 py-4">
          <p className="text-sm font-semibold text-emerald-900">
            Brief generated in {fmtElapsed(elapsedS)}.
          </p>
          <p className="mt-1 text-xs text-emerald-800">
            All 8 pipeline stages completed. Ready to view.
          </p>
          <Link
            href={`/briefs/${status.brief_id}`}
            className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700"
          >
            View brief
            <span aria-hidden>→</span>
          </Link>
        </div>
      )}

      {isFailed && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <p className="font-semibold">Pipeline failed</p>
          <p className="mt-1 text-rose-700">
            {status?.error_message ?? "Unknown error."}
          </p>
        </div>
      )}

      {/* Footer */}
      <div className="space-y-3 border-t border-slate-200 pt-4">
        <button
          onClick={onReset}
          className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-700"
        >
          ← Start another
        </button>
        <p className="text-xs leading-relaxed text-slate-400">
          <span aria-hidden className="mr-1">
            ⓘ
          </span>
          Each node writes to <span className="font-mono">etl_run_log.node_history</span>{" "}
          when it starts and finishes. The UI polls every 2 seconds for the live state.
        </p>
      </div>
    </div>
  );
}
