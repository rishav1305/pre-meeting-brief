export function AuditPanel({ auditData }: { auditData: Record<string, unknown> | null }) {
  if (!auditData) return null;
  return (
    <details className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-xs">
      <summary className="cursor-pointer font-medium text-slate-700">
        Data quality & sources ({Object.keys(auditData).length})
      </summary>
      <pre className="mt-2 overflow-x-auto text-slate-600">
        {JSON.stringify(auditData, null, 2)}
      </pre>
    </details>
  );
}
