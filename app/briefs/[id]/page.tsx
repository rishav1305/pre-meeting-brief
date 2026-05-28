import { notFound } from "next/navigation";

import { AuditPanel } from "@/components/AuditPanel";
import { ConfidenceDot } from "@/components/ConfidenceDot";
import { DashboardSection } from "@/components/DashboardSection";
import { ThesisFitBadge } from "@/components/ThesisFitBadge";
import { fetchBrief } from "@/lib/api";

export default async function BriefPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let brief;
  try {
    brief = await fetchBrief(id);
  } catch {
    notFound();
  }
  if (!brief) notFound();

  const { company, people, traction, thesis_fit, industry_deepdive, market_deepdive } = brief;

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-8">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <header className="border-b border-slate-200 pb-6">
          <div className="flex items-baseline justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {company.tags?.[0] ?? "Company"}
              </p>
              <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
                {company.domain}
              </h1>
              <p className="mt-1 text-sm text-slate-600">{company.description}</p>
            </div>
            <ThesisFitBadge score={thesis_fit?.score ?? null} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {company.growth_stage?.replace(/_/g, " ")}
            </span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {company.last_round_type?.replace(/_/g, " ")}
            </span>
            {company.post_money_valuation_usd && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                ${(company.post_money_valuation_usd / 1e9).toFixed(1)}B post
              </span>
            )}
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {people?.employee_count ? `${people.employee_count.toLocaleString()} employees` : "—"}
            </span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {company.hq_city ? `${company.hq_city}, ${company.hq_country}` : company.hq_country}
            </span>
          </div>
        </header>

        {/* Above-the-fold dashboard */}
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <DashboardSection title="Thesis Fit" subtitle="Renegade — Markets That Matter">
            {thesis_fit ? (
              <>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold">Score:</span> {thesis_fit.score}/5
                </p>
                <p className="mt-2 text-sm text-slate-700">
                  <span className="font-semibold">Reasoning:</span> {thesis_fit.reasoning}
                </p>
                <p className="mt-2 text-sm text-slate-700">
                  <span className="font-semibold">Bear case:</span> {thesis_fit.bear_case}
                </p>
              </>
            ) : (
              <p className="text-sm text-slate-500">Not yet generated.</p>
            )}
          </DashboardSection>

          <DashboardSection title="Funding">
            {company.total_raised_usd && (
              <p className="text-sm text-slate-700">
                Total raised: <strong>${(company.total_raised_usd / 1e9).toFixed(2)}B</strong>{" "}
                <ConfidenceDot
                  confidence="green"
                  sources={["PitchBook", "Specter", "Crunchbase"]}
                />
              </p>
            )}
            <p className="mt-1 text-sm text-slate-700">
              Last round: <strong>{company.last_round_type?.replace(/_/g, " ")}</strong>
            </p>
            <p className="mt-1 text-sm text-slate-700">
              Investors:{" "}
              <span className="text-slate-600">{company.investors?.slice(0, 3).join(", ")}</span>
            </p>
          </DashboardSection>

          <DashboardSection title="Team">
            {people?.founders?.slice(0, 3).map((f: any) => (
              <p key={f.full_name} className="text-sm text-slate-700">
                <strong>{f.full_name}</strong> · {f.title}{" "}
                {f.prior_exits?.[0] && (
                  <span className="text-xs text-slate-500">— {f.prior_exits[0]}</span>
                )}
              </p>
            ))}
          </DashboardSection>

          <DashboardSection title="Traction" subtitle="Signals">
            {traction?.new_highlights?.map((h: string) => (
              <p key={h} className="text-sm text-slate-700">
                ⚡ {h.replace(/_/g, " ")}
              </p>
            ))}
            {traction?.highlights?.slice(0, 3).map((h: string) => (
              <p key={h} className="text-sm text-slate-700">
                · {h.replace(/_/g, " ")}
              </p>
            ))}
          </DashboardSection>
        </div>

        {/* Prior engagement */}
        {brief.prior_interactions?.length > 0 && (
          <div className="mt-6">
            <DashboardSection title="Prior Engagement" subtitle="Outside the 3-month window">
              <ul className="space-y-1.5 text-sm text-slate-700">
                {brief.prior_interactions.map((i: any, idx: number) => (
                  <li key={idx}>
                    <span className="text-slate-500">{i.date}</span> · {i.type} —{" "}
                    {i.summary}
                  </li>
                ))}
              </ul>
            </DashboardSection>
          </div>
        )}

        {/* Below-the-fold: prose deep-dives */}
        {industry_deepdive && (
          <div className="mt-6">
            <DashboardSection title="Industry Deep-Dive">
              <p className="text-sm leading-relaxed text-slate-700">{industry_deepdive}</p>
            </DashboardSection>
          </div>
        )}

        {market_deepdive && (
          <div className="mt-4">
            <DashboardSection title="Market Deep-Dive">
              <p className="text-sm leading-relaxed text-slate-700">{market_deepdive}</p>
            </DashboardSection>
          </div>
        )}

        {brief.key_engagement_questions?.length > 0 && (
          <div className="mt-4">
            <DashboardSection title="Key Questions">
              <ol className="space-y-2 text-sm text-slate-700">
                {brief.key_engagement_questions.map((q: string, i: number) => (
                  <li key={i}>
                    <span className="font-semibold">{i + 1}.</span> {q}
                  </li>
                ))}
              </ol>
            </DashboardSection>
          </div>
        )}

        <AuditPanel brief={brief} />

        <footer className="mt-8 border-t border-slate-200 pt-4 text-xs text-slate-500">
          Generated {new Date(brief.generated_at).toLocaleString()} · Partner: {brief.partner}
        </footer>
      </div>
    </main>
  );
}
