export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-wider text-slate-500">
          Renegade Capital
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-900">
          Pre-Meeting Brief
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Phase 0 — deployed. Phase 1 (schema, fixtures, agenda) in progress.
        </p>
        <p className="mt-8 text-sm text-slate-500">
          See the architecture approach at{' '}
          <a
            className="underline underline-offset-2 hover:text-slate-700"
            href="/pre-meeting-brief/approach"
          >
            /approach
          </a>
          .
        </p>
      </div>
    </main>
  );
}
