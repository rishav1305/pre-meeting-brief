type Confidence = "green" | "yellow" | "red";

const STYLES: Record<Confidence, string> = {
  green: "bg-emerald-500 ring-emerald-100",
  yellow: "bg-amber-400 ring-amber-100",
  red: "bg-rose-500 ring-rose-100",
};

/**
 * Tiering rule (matches approach.md §8.3):
 *   green  — 2+ independent sources contributing the field
 *   yellow — 1 source, or modeled / estimated values
 *   red    — single source AND in conflict, or web-only with no canonical backing
 */
export function confidenceFromSources(
  sourceCount: number,
  opts?: { modeled?: boolean; inConflict?: boolean },
): Confidence {
  if (opts?.inConflict && sourceCount <= 1) return "red";
  if (opts?.modeled) return "yellow";
  if (sourceCount >= 2) return "green";
  if (sourceCount === 1) return "yellow";
  return "red";
}

export function ConfidenceDot({
  confidence,
  sources,
  label,
}: {
  confidence: Confidence;
  sources: string[];
  label?: string;
}) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ring-2 ${STYLES[confidence]}`}
      title={`${label ?? "Source"}: ${sources.join(", ")}`}
      aria-label={`Confidence ${confidence}: ${sources.join(", ")}`}
    />
  );
}
