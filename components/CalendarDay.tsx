import { CalendarEventCard } from "@/components/CalendarEventCard";
import type { TaggedAgendaItem } from "@/lib/types";

/**
 * Returns a human-friendly day heading for a YYYY-MM-DD meeting_date.
 * Uses the user's local timezone; "Today" / "Tomorrow" prefixes when applicable.
 *
 * meeting_date is a bare DATE (no time / no tz) — parsing it as `${date}T00:00:00`
 * makes it local-midnight, which matches what the user intuitively means by "that day".
 */
function formatDayHeading(dateStr: string): string {
  const dt = new Date(`${dateStr}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);

  const pretty = dt.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });

  if (dt.getTime() === today.getTime()) return `Today · ${pretty}`;
  if (dt.getTime() === tomorrow.getTime()) return `Tomorrow · ${pretty}`;
  return pretty;
}

export function CalendarDay({ date, items }: { date: string; items: TaggedAgendaItem[] }) {
  const heading = formatDayHeading(date);
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold text-slate-700">{heading}</h3>
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-xs tabular-nums text-slate-400">
          {items.length} {items.length === 1 ? "meeting" : "meetings"}
        </span>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <CalendarEventCard key={item.event_id} item={item} />
        ))}
      </div>
    </section>
  );
}
