type AuditEntry = { field?: string; source?: string };
type AuditBlock = { fields?: AuditEntry[] } | null;
type Props = {
  brief: {
    audit_company?: AuditBlock;
    audit_people?: AuditBlock;
    audit_traction_metrics?: AuditBlock;
  };
};

export function HowAssembled({ brief }: Props) {
  const auditEntries: AuditEntry[] = [
    ...(brief.audit_company?.fields ?? []),
    ...(brief.audit_people?.fields ?? []),
    ...(brief.audit_traction_metrics?.fields ?? []),
  ];
  const sources = Array.from(
    new Set(auditEntries.map((e) => e.source).filter((s): s is string => !!s)),
  );
  return (
    <details className="mt-4 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm">
      <summary className="cursor-pointer font-medium text-slate-700">
        How this brief was assembled
      </summary>
      <div className="mt-3 space-y-2 text-slate-600">
        <p>
          Sources that contributed to this brief:{" "}
          {sources.length > 0 ? sources.join(", ") : <span className="text-slate-400">—</span>}.
        </p>
        <p>
          The pipeline ran <code>resolve_company</code> → <code>fetch_all</code> (parallel) →{" "}
          <code>merge_canonical</code> → <code>synthesise_brief</code>, producing this output.
          See the full architecture and stage breakdown at{" "}
          <a className="underline" href="/pre-meeting-brief/pipeline">
            /pipeline
          </a>
          .
        </p>
        <p className="text-xs text-slate-500">
          Phase 2 will replace this static summary with a live trace: tool calls, timings, and the
          synthesis agent&apos;s draft → critique → revise iterations.
        </p>
      </div>
    </details>
  );
}
