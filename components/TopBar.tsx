import Link from "next/link";

export function TopBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="flex shrink-0 items-baseline gap-2">
          <span className="text-base font-semibold text-slate-900">Pre-Meeting Brief</span>
          <span className="hidden text-xs uppercase tracking-wider text-slate-400 lg:inline">
            · Capital Numbers · AI-Native Tech Lead
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link
            href="/"
            className="rounded-md px-3 py-1.5 text-slate-700 transition hover:bg-slate-100"
          >
            Agenda
          </Link>
          <Link
            href="/pipeline"
            className="rounded-md px-3 py-1.5 text-slate-700 transition hover:bg-slate-100"
          >
            Pipeline
          </Link>
          <Link
            href="/approach"
            className="rounded-md px-3 py-1.5 text-slate-700 transition hover:bg-slate-100"
          >
            Approach
          </Link>
          <Link
            href="/admin"
            className="ml-2 inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
          >
            Generate brief
            <span aria-hidden>→</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}
