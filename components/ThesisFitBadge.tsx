import type { ThesisFitScore } from "@/lib/types";

const COLORS: Record<ThesisFitScore, string> = {
  5: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  4: "bg-lime-100 text-lime-800 ring-lime-300",
  3: "bg-amber-100 text-amber-800 ring-amber-300",
  2: "bg-orange-100 text-orange-800 ring-orange-300",
  1: "bg-rose-100 text-rose-800 ring-rose-300",
};

export function ThesisFitBadge({ score }: { score: ThesisFitScore | null }) {
  if (!score) return <span className="text-slate-400 text-sm">—</span>;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${COLORS[score]}`}
    >
      Thesis fit {score}/5
    </span>
  );
}
