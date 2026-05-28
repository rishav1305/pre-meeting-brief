/**
 * API base resolver.
 *
 * In server components, Node's fetch needs an absolute URL — there is no
 * "current page origin" to resolve relative paths against. In the browser,
 * relative paths work fine. We resolve in this priority:
 *   1. Explicit override via NEXT_PUBLIC_API_BASE
 *   2. Vercel-provided VERCEL_URL (set on every deployment)
 *   3. Relative fallback "/pre-meeting-brief/api" (works in browser + local dev)
 */
function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window === "undefined" && process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}/api`;
  }
  return "/pre-meeting-brief/api";
}

export async function fetchAgenda(partner: string) {
  const base = resolveApiBase();
  const res = await fetch(`${base}/agenda?partner=${encodeURIComponent(partner)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Agenda fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchBrief(briefId: string) {
  const base = resolveApiBase();
  const res = await fetch(`${base}/briefs/${briefId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Brief fetch failed: ${res.status}`);
  return res.json();
}
