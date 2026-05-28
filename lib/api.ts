const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/pre-meeting-brief/api";

export async function fetchAgenda(partner: string) {
  const res = await fetch(`${API_BASE}/agenda?partner=${encodeURIComponent(partner)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Agenda fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchBrief(briefId: string) {
  const res = await fetch(`${API_BASE}/briefs/${briefId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Brief fetch failed: ${res.status}`);
  return res.json();
}
