"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Run = {
  run_id: string;
  started_at: string | null;
  completed_at: string | null;
  status: "running" | "complete" | "failed" | "merged";
  duration_ms: number | null;
  partner: string | null;
  company_domain: string | null;
  brief_id: string | null;
  current_node: string | null;
};

const STATUS_STYLE: Record<string, string> = {
  running: "bg-amber-100 text-amber-700",
  merged: "bg-sky-100 text-sky-700",
  complete: "bg-emerald-100 text-emerald-700",
  failed: "bg-rose-100 text-rose-700",
};

/**
 * Recent runs panel for /admin.
 *
 * Polls /pre-meeting-brief/api/triggers/runs every 10s so a running row
 * progresses without a manual refresh. Rendered below the form when the
 * admin is authed and not viewing a specific run.
 */
export function RecentRuns() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch(
          "/pre-meeting-brief/api/triggers/runs?limit=10",
          { cache: "no-store" },
        );
        if (!res.ok) {
          if (!cancelled) {
            setError(`HTTP ${res.status}`);
            setLoading(false);
          }
          return;
        }
        const data = (await res.json()) as { items: Run[] };
        if (!cancelled) {
          setRuns(data.items);
          setError(null);
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "failed to load");
          setLoading(false);
        }
      }
    }

    void load();
    const t = setInterval(load, 10_000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-slate-500">Loading recent runs…</p>;
  }
  if (error) {
    return (
      <p className="text-sm text-rose-700">
        Couldn’t load recent runs ({error}).
      </p>
    );
  }
  if (runs.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No runs yet. Submit the form above to start one.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {runs.map((r) => (
        <li key={r.run_id}>
          <RunRow run={r} />
        </li>
      ))}
    </ul>
  );
}

function RunRow({ run }: { run: Run }) {
  const statusStyle =
    STATUS_STYLE[run.status] ?? "bg-slate-100 text-slate-700";
  const rightLabel = (() => {
    if (run.status === "running") {
      if (run.current_node) return `↻ ${run.current_node}`;
      if (run.started_at) return `running for ${fmtSinceStart(run.started_at)}`;
      return "running";
    }
    if (run.duration_ms != null) return fmtDuration(run.duration_ms);
    return "";
  })();

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm">
      <span
        className={`inline-flex shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${statusStyle}`}
      >
        {run.status}
      </span>
      <span className="font-medium text-slate-900">
        {run.company_domain ?? "—"}
      </span>
      <span className="text-slate-400">·</span>
      <span className="text-slate-600">{run.partner ?? "—"}</span>
      {rightLabel && (
        <span className="ml-auto font-mono text-xs text-slate-500">
          {rightLabel}
        </span>
      )}
      {run.brief_id && (
        <Link
          href={`/briefs/${run.brief_id}`}
          className={
            (rightLabel ? "ml-2" : "ml-auto") +
            " inline-flex shrink-0 items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          }
        >
          View brief →
        </Link>
      )}
    </div>
  );
}

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  return `${m}m ${rem.toString().padStart(2, "0")}s`;
}

function fmtSinceStart(startedIso: string): string {
  const started = new Date(startedIso).getTime();
  if (Number.isNaN(started)) return "";
  const ms = Date.now() - started;
  if (ms < 0) return "0s";
  return fmtDuration(ms);
}
