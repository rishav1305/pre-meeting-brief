import { BriefCard } from "@/components/BriefCard";
import { fetchAgenda } from "@/lib/api";
import type { AgendaResponse } from "@/lib/types";

const PARTNER = "Devon";

export default async function Home() {
  let agenda: AgendaResponse | null = null;
  let error: string | null = null;
  try {
    agenda = await fetchAgenda(PARTNER);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12">
      <div className="mx-auto max-w-4xl">
        <header className="border-b border-slate-200 pb-6">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Take-home submission · Capital Numbers · AI-Native Tech Lead
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
            Today&apos;s Agenda
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Pre-meeting briefs for upcoming first meetings with new companies (rolling 3-month
            window). Demo client: Renegade Capital · Partner: {PARTNER}.
          </p>
        </header>

        <section className="mt-8">
          {error && (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              Could not load agenda: {error}
            </div>
          )}
          {agenda && agenda.items.length === 0 && (
            <p className="text-sm text-slate-500">No meetings scheduled.</p>
          )}
          {agenda && agenda.items.length > 0 && (
            <div className="space-y-3">
              {agenda.items.map((item) => (
                <BriefCard key={item.event_id} item={item} />
              ))}
            </div>
          )}
        </section>

        <footer className="mt-12 border-t border-slate-200 pt-6 text-xs text-slate-500">
          <a className="underline underline-offset-2" href="/pre-meeting-brief/approach">
            Architecture approach
          </a>
        </footer>
      </div>
    </main>
  );
}
