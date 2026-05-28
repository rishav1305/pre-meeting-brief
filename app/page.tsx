import Link from "next/link";

import { BriefCard } from "@/components/BriefCard";
import { fetchAgenda } from "@/lib/api";
import type { AgendaResponse } from "@/lib/types";

const PARTNERS = ["Devon", "Sara", "Joe"] as const;
type Partner = (typeof PARTNERS)[number];
const DEFAULT_PARTNER: Partner = "Devon";

function isPartner(s: string | undefined): s is Partner {
  return !!s && (PARTNERS as readonly string[]).includes(s);
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ partner?: string }>;
}) {
  const params = await searchParams;
  const partner: Partner = isPartner(params.partner) ? params.partner : DEFAULT_PARTNER;

  let agenda: AgendaResponse | null = null;
  let error: string | null = null;
  try {
    agenda = await fetchAgenda(partner);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  const items = agenda?.items ?? [];
  const briefedCount = items.filter((i) => i.brief_id).length;
  const totalCount = items.length;
  const scoreCounts = items.reduce(
    (acc, i) => {
      if (i.thesis_fit_score) acc[i.thesis_fit_score] = (acc[i.thesis_fit_score] ?? 0) + 1;
      return acc;
    },
    {} as Record<number, number>,
  );

  return (
    <main className="px-6 py-10 sm:py-14">
      <div className="mx-auto max-w-5xl">
        {/* Hero */}
        <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 px-8 py-10 shadow-sm">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div className="max-w-2xl">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Today&apos;s agenda
              </p>
              <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
                Pre-meeting briefs, on tap.
              </h1>
              <p className="mt-4 text-base text-slate-600">
                Each card below is a brief assembled by a 4-agent LangGraph pipeline — Qualification,
                Research (Claude <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">web_search</code>),
                Data Quality, and Synthesis (forced tool_use for guaranteed JSON). Click any card to
                read the dashboard, or generate a fresh one for any domain.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <Link
                  href="/admin"
                  className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
                >
                  Generate a brief
                  <span aria-hidden>→</span>
                </Link>
                <Link
                  href="/approach"
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                >
                  Read the approach
                </Link>
                <Link
                  href="/pipeline"
                  className="text-sm text-slate-600 underline-offset-4 hover:text-slate-900 hover:underline"
                >
                  See the pipeline →
                </Link>
              </div>
            </div>
            {/* Stats strip */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-wider text-slate-500">Briefs ready</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
                  {briefedCount} <span className="text-base font-normal text-slate-400">/ {totalCount}</span>
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-wider text-slate-500">Thesis fit 5/5</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-600">
                  {scoreCounts[5] ?? 0}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-wider text-slate-500">Thesis fit 3/5</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-600">
                  {scoreCounts[3] ?? 0}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-wider text-slate-500">Off thesis</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-500">
                  {(scoreCounts[1] ?? 0) + (scoreCounts[2] ?? 0)}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Partner switcher + section heading */}
        <section className="mt-10">
          <div className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Viewing agenda for partner
              </h2>
              <div className="mt-2 flex items-center gap-1">
                {PARTNERS.map((p) => {
                  const active = p === partner;
                  return (
                    <Link
                      key={p}
                      href={p === DEFAULT_PARTNER ? "/" : `/?partner=${p}`}
                      className={
                        active
                          ? "rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white shadow-sm"
                          : "rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                      }
                    >
                      {p}
                    </Link>
                  );
                })}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Partners are senior investors at the VC firm. Each has their own calendar; the
                pipeline scopes data, prior-engagement, and synthesis to the partner the brief is
                generated for.
              </p>
            </div>
            <p className="text-xs text-slate-400">
              Demo client: <span className="font-medium text-slate-600">Renegade Capital</span>
            </p>
          </div>

          <div className="mt-4">
            {error && (
              <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                Could not load agenda: {error}
              </div>
            )}
            {agenda && items.length === 0 && (
              <div className="rounded-md border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500">
                No meetings scheduled for <span className="font-medium text-slate-700">{partner}</span> in the next 14 days.
              </div>
            )}
            {agenda && items.length > 0 && (
              <div className="space-y-3">
                {items.map((item) => (
                  <BriefCard key={item.event_id} item={item} />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
