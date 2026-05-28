import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-3 px-6 py-6 text-xs text-slate-500 sm:flex-row sm:items-center">
        <div className="space-y-0.5">
          <p>
            Take-home submission for the{" "}
            <strong className="font-semibold text-slate-700">Capital Numbers AI-Native Tech Lead</strong>{" "}
            role · designed around{" "}
            <strong className="font-semibold text-slate-700">Renegade Capital</strong> as the demo VC client.
          </p>
          <p className="text-slate-400">
            Built by <a className="underline-offset-2 hover:underline" href="https://rishavchatterjee.com">Rishav Chatterjee</a> · 2026-05-29
          </p>
        </div>
        <div className="flex items-center gap-4">
          <a
            className="hover:text-slate-700"
            href="https://github.com/rishav1305/pre-meeting-brief"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <Link className="hover:text-slate-700" href="/approach">
            Approach
          </Link>
          <Link className="hover:text-slate-700" href="/pipeline">
            Pipeline
          </Link>
          <Link className="hover:text-slate-700" href="/admin">
            Admin
          </Link>
        </div>
      </div>
    </footer>
  );
}
