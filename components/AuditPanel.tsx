/**
 * Consolidated brief audit panel.
 *
 * Renders three sub-panels (company, people, traction) — each a table of
 * per-field provenance pulled from the brief's frozen audit JSONB columns.
 * Each row shows: field · primary source · pulled-at timestamp, with any
 * subsequent occurrences of the same field stacked underneath as confirming
 * sources.
 *
 * Source-name → color-pill mapping is hardcoded to the 4 providers; anything
 * else falls through to a neutral slate pill. The "primary" source carries
 * `●`, confirming sources carry `○`.
 */

type AuditField = {
  field: string;
  source?: string;
  pulled_at?: string;
};

type AuditBlock = { fields?: AuditField[] } | null | undefined;

type DataQualityFlag = {
  field: string;
  issue: string;
  severity: string;
  source_a?: string;
  value_a?: string;
  source_b?: string;
  value_b?: string;
};

type BriefShape = {
  audit_company?: AuditBlock;
  audit_people?: AuditBlock;
  audit_traction_metrics?: AuditBlock;
  data_quality_flags?: DataQualityFlag[];
};

// ----- helpers ---------------------------------------------------------------

const PILL_STYLES: Record<string, string> = {
  specter: "bg-indigo-100 text-indigo-700",
  crunchbase: "bg-emerald-100 text-emerald-700",
  pitchbook: "bg-purple-100 text-purple-700",
  attio: "bg-amber-100 text-amber-700",
  web: "bg-slate-200 text-slate-700",
  web_search: "bg-slate-200 text-slate-700",
};

function pillFor(source: string | undefined): string {
  if (!source) return "bg-slate-100 text-slate-500";
  const key = source.toLowerCase().replace(/[\s-]/g, "_");
  if (key === "missing") return "bg-rose-50 text-rose-700";
  return PILL_STYLES[key] ?? "bg-slate-100 text-slate-600";
}

function formatPulledAt(ts: string | undefined): string {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts;
    // Compact: 2026-05-28 11:38Z
    const iso = d.toISOString();
    return `${iso.slice(0, 10)} ${iso.slice(11, 16)}Z`;
  } catch {
    return ts;
  }
}

type GroupedRow = {
  field: string;
  primary: AuditField;
  confirmers: AuditField[];
};

/**
 * Collapse the flat audit list into one row per field. First occurrence is the
 * primary winner; subsequent occurrences are confirming sources stacked under.
 *
 * Stable: input order is preserved both across fields and within a field's
 * confirming list.
 */
function groupAuditFields(fields: AuditField[]): GroupedRow[] {
  const seen = new Map<string, GroupedRow>();
  const order: string[] = [];
  for (const entry of fields) {
    const name = entry.field;
    if (!name) continue;
    const existing = seen.get(name);
    if (existing) {
      existing.confirmers.push(entry);
    } else {
      seen.set(name, { field: name, primary: entry, confirmers: [] });
      order.push(name);
    }
  }
  return order.map((n) => seen.get(n)!).filter(Boolean);
}

// ----- sub-components --------------------------------------------------------

function SourcePill({
  source,
  marker,
}: {
  source: string | undefined;
  marker: "primary" | "confirm";
}) {
  const symbol = marker === "primary" ? "●" : "○";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${pillFor(
        source,
      )}`}
    >
      <span aria-hidden="true">{symbol}</span>
      <span>{source ?? "unknown"}</span>
    </span>
  );
}

function AuditTable({ rows }: { rows: GroupedRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="px-4 py-3 text-xs text-slate-500">
        No provenance entries recorded for this section.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs text-slate-700">
        <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-4 py-2 font-medium">Field</th>
            <th className="px-4 py-2 font-medium">Source</th>
            <th className="px-4 py-2 font-medium">Pulled at</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.field} className="align-top">
              <td className="px-4 py-2 font-mono text-[11.5px] text-slate-800">{row.field}</td>
              <td className="px-4 py-2">
                <div className="flex flex-col gap-1">
                  <SourcePill source={row.primary.source} marker="primary" />
                  {row.confirmers.map((c, i) => (
                    <SourcePill
                      key={`${row.field}-conf-${i}`}
                      source={c.source}
                      marker="confirm"
                    />
                  ))}
                </div>
              </td>
              <td className="px-4 py-2 font-mono text-[11px] text-slate-500">
                {formatPulledAt(row.primary.pulled_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditSubsection({
  title,
  block,
  defaultOpen,
}: {
  title: string;
  block: AuditBlock;
  defaultOpen: boolean;
}) {
  const fields = block?.fields ?? [];
  const rows = groupAuditFields(fields);
  return (
    <details
      className="group rounded-md border border-slate-200 bg-white"
      open={defaultOpen}
    >
      <summary className="flex cursor-pointer items-center justify-between px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
        <span>
          {title}{" "}
          <span className="text-xs font-normal text-slate-500">({rows.length} fields)</span>
        </span>
        <span className="text-xs text-slate-400 group-open:hidden">expand</span>
        <span className="hidden text-xs text-slate-400 group-open:inline">collapse</span>
      </summary>
      <div className="border-t border-slate-200">
        <AuditTable rows={rows} />
      </div>
    </details>
  );
}

function FlagsTeaser({ flags }: { flags: DataQualityFlag[] | undefined }) {
  if (!flags || flags.length === 0) {
    return (
      <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Data quality:</span> no conflicts surfaced
        for this brief — all source values within tolerance per the priority chains.
      </div>
    );
  }
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900">
      <p className="font-medium">
        ⚠ {flags.length} data-quality {flags.length === 1 ? "flag" : "flags"} detected during merge.
      </p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5">
        {flags.slice(0, 4).map((f, i) => (
          <li key={`${f.field}-${i}`}>
            <code className="font-mono text-[11.5px]">{f.field}</code> — {f.issue}
            {f.source_a && f.source_b && (
              <>
                {" "}
                ({f.source_a}={f.value_a ?? "—"}, {f.source_b}={f.value_b ?? "—"})
              </>
            )}
          </li>
        ))}
        {flags.length > 4 && (
          <li className="text-amber-700">… {flags.length - 4} more in /runs.</li>
        )}
      </ul>
    </div>
  );
}

// ----- root component --------------------------------------------------------

export function AuditPanel({ brief }: { brief: BriefShape }) {
  const company = brief.audit_company;
  const people = brief.audit_people;
  const traction = brief.audit_traction_metrics;

  const hasAnyAudit =
    (company?.fields?.length ?? 0) > 0 ||
    (people?.fields?.length ?? 0) > 0 ||
    (traction?.fields?.length ?? 0) > 0;

  return (
    <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <header>
        <h2 className="text-base font-semibold text-slate-900">
          How this brief was assembled
        </h2>
        <p className="mt-1 text-xs text-slate-600">
          Each fact carries a provenance record stamped at merge time. Rows are grouped by field
          with the winning source on top (<span aria-hidden="true">●</span>) and any confirming
          sources stacked underneath (<span aria-hidden="true">○</span>).
        </p>
      </header>

      <div className="mt-4">
        <FlagsTeaser flags={brief.data_quality_flags} />
      </div>

      {!hasAnyAudit ? (
        <div className="mt-4 rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-xs text-slate-500">
          Audit data not available for this brief. Re-generate via{" "}
          <a className="underline" href="/pre-meeting-brief/admin">
            /admin
          </a>{" "}
          to capture full provenance.
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <AuditSubsection title="Company profile" block={company} defaultOpen={true} />
          <AuditSubsection title="People" block={people} defaultOpen={false} />
          <AuditSubsection title="Traction" block={traction} defaultOpen={false} />
        </div>
      )}

      <div className="mt-6 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
        <p className="font-medium text-slate-700">Pipeline that produced this brief</p>
        <p className="mt-1">
          <code>resolve_company</code> → <code>fetch_all</code> (4 providers concurrent;
          1 via real MCP subprocess) → <code>research_agent</code> (Claude web_search) →{" "}
          <code>merge_canonical</code> (deterministic priority chains + 6 conflict detectors) →{" "}
          <code>data_quality_agent</code> → <code>synthesise_brief</code> (Claude Sonnet 4.6 with
          forced tool_use).
        </p>
        <p className="mt-1">
          See the full stage breakdown at{" "}
          <a className="underline" href="/pre-meeting-brief/pipeline">
            /pipeline
          </a>
          .
        </p>
      </div>
    </section>
  );
}
