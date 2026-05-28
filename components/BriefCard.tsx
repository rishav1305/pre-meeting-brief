import Link from "next/link";

import { ThesisFitBadge } from "@/components/ThesisFitBadge";
import type { AgendaItem } from "@/lib/types";

export function BriefCard({ item }: { item: AgendaItem }) {
  const hasBrief = !!item.brief_id;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500">
            {new Date(item.meeting_date).toLocaleDateString("en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </div>
          <h3 className="mt-1 text-lg font-semibold text-slate-900">{item.company_domain}</h3>
          {item.company_description && (
            <p className="mt-2 line-clamp-2 text-sm text-slate-600">{item.company_description}</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            {item.company_stage && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                {item.company_stage.replace(/_/g, " ")}
              </span>
            )}
            {item.company_last_round && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                {item.company_last_round.replace(/_/g, " ")}
              </span>
            )}
            <ThesisFitBadge score={item.thesis_fit_score} />
          </div>
        </div>
        {hasBrief ? (
          <Link
            href={`/briefs/${item.brief_id}`}
            className="shrink-0 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
          >
            Read brief →
          </Link>
        ) : (
          <span className="shrink-0 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700">
            Brief pending
          </span>
        )}
      </div>
    </div>
  );
}
