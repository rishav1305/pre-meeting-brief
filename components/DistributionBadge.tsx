type DistributionAttempt = {
  channel: string;
  status: string;
  endpoint?: string;
  brief_link?: string;
  target?: {
    calendar_id?: string;
    event_id?: string | null;
    meeting_date?: string | null;
    company_domain?: string | null;
  };
  attempted_at?: string;
  error?: string | null;
  note?: string | null;
};

function formatAttemptedAt(ts: string | undefined): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function DistributionBadge({
  log,
}: {
  log: DistributionAttempt[] | undefined | null;
}) {
  if (!log || log.length === 0) {
    return (
      <div className="mt-6 rounded-md border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Distribution:</span> not yet attached to
        a calendar event for this brief.
      </div>
    );
  }
  // Show the latest attempt prominently; older attempts collapse into a count.
  const latest = log[log.length - 1];
  const prior = log.length - 1;
  const channelLabel = latest.channel === "google_calendar" ? "Google Calendar" : latest.channel;
  const targetLabel = latest.target?.event_id
    ? `event ${latest.target.event_id.slice(0, 8)}…`
    : latest.target?.meeting_date
      ? `${latest.target.meeting_date} (no event match)`
      : "no target";

  const statusColor =
    latest.status === "sent"
      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
      : latest.status === "logged"
        ? "border-sky-200 bg-sky-50 text-sky-900"
        : "border-amber-200 bg-amber-50 text-amber-900";
  const statusLabel =
    latest.status === "sent"
      ? "Attached"
      : latest.status === "logged"
        ? "Payload built (POC mock)"
        : latest.status;

  return (
    <div className={`mt-6 rounded-md border px-4 py-3 text-xs ${statusColor}`}>
      <p className="font-medium">
        Distribution → {channelLabel}: {statusLabel}
      </p>
      <p className="mt-1 text-[11.5px] opacity-80">
        Target: {targetLabel} · attempted {formatAttemptedAt(latest.attempted_at)}
      </p>
      {latest.note && (
        <p className="mt-1 text-[11.5px] italic opacity-70">{latest.note}</p>
      )}
      {prior > 0 && (
        <p className="mt-1 text-[11.5px] opacity-60">
          + {prior} earlier attempt{prior === 1 ? "" : "s"}
        </p>
      )}
    </div>
  );
}
