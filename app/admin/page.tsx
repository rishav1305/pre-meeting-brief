"use client";
import { useEffect, useState } from "react";

import { AdminForm } from "@/components/AdminForm";
import { RecentRuns } from "@/components/RecentRuns";
import { RunStatus } from "@/components/RunStatus";

const STORAGE_KEY = "pmb-admin-pw";

export default function AdminPage() {
  const [password, setPassword] = useState<string | null>(null);
  const [pendingPw, setPendingPw] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (stored) setPassword(stored);
  }, []);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(null);
    // Validate by attempting a dummy status fetch — but simpler: just trust + let the first
    // POST fail with 401 if wrong. Save and continue.
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, pendingPw);
    }
    setPassword(pendingPw);
  }

  function handleLogout() {
    if (typeof window !== "undefined") localStorage.removeItem(STORAGE_KEY);
    setPassword(null);
    setPendingPw("");
    setRunId(null);
  }

  // When a run is in flight, the card-per-node timeline needs a touch more
  // horizontal room than the login/launch forms. Widen to max-w-3xl in that
  // state only; keep the form compact at max-w-2xl.
  const containerWidth = runId !== null ? "max-w-3xl" : "max-w-2xl";

  return (
    <main className="px-6 py-10 sm:py-14">
      <div className={`mx-auto ${containerWidth}`}>
        <header className="pb-6">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Admin
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
            Generate a brief
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Type any domain (Anduril, Hadrian, Modal, Ramp, Glean, Mercury are pre-seeded —
            try a new domain to see the full pipeline run). Watch the agentic pipeline
            assemble the brief in real time.
          </p>
        </header>

        <section className="mt-8">
          {password === null && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                  Admin password
                </label>
                <input
                  type="password"
                  value={pendingPw}
                  onChange={(e) => setPendingPw(e.target.value)}
                  required
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              {authError && (
                <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                  {authError}
                </div>
              )}
              <button
                type="submit"
                className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                Continue
              </button>
            </form>
          )}

          {password !== null && runId === null && (
            <div className="space-y-10">
              <AdminForm password={password} onLaunched={setRunId} />

              <div>
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Recent pipeline runs
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Last 10 runs across all partners. Refreshes every 10 seconds.
                </p>
                <div className="mt-3">
                  <RecentRuns />
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-700"
              >
                Sign out
              </button>
            </div>
          )}

          {password !== null && runId !== null && (
            <RunStatus runId={runId} onReset={() => setRunId(null)} />
          )}
        </section>

      </div>
    </main>
  );
}
