import Link from "next/link";

import { ThesisFitBadge } from "@/components/ThesisFitBadge";
import type { TaggedAgendaItem, Partner } from "@/lib/types";

const PARTNER_BADGE: Record<Partner, string> = {
  Devon: "bg-indigo-100 text-indigo-700 ring-1 ring-indigo-200",
  Sara: "bg-teal-100 text-teal-700 ring-1 ring-teal-200",
  Joe: "bg-amber-100 text-amber-700 ring-1 ring-amber-200",
};

const PARTNER_STRIPE: Record<Partner, string> = {
  Devon: "bg-indigo-500",
  Sara: "bg-teal-500",
  Joe: "bg-amber-500",
};

export function CalendarEventCard({ item }: { item: TaggedAgendaItem }) {
  const hasBrief = !!item.brief_id;
  const partner = item.partner as Partner;
  const stripe = PARTNER_STRIPE[partner] ?? "bg-slate-400";
  const badge = PARTNER_BADGE[partner] ?? "bg-slate-100 text-slate-700 ring-1 ring-slate-200";

  return (
    <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow">
      {/* Partner color stripe */}
      <div className={`absolute inset-y-0 left-0 w-1 ${stripe}`} aria-hidden />
      <div className="flex items-start justify-between gap-4 p-5 pl-6">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${badge}`}
            >
              {partner}
            </span>
            <h3 className="truncate text-base font-semibold text-slate-900">
              {item.company_domain}
            </h3>
          </div>
          {item.company_description && (
            <p className="mt-2 line-clamp-1 text-sm text-slate-600">{item.company_description}</p>
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
