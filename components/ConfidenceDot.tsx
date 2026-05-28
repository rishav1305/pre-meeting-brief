type Confidence = "green" | "yellow" | "red";

const STYLES: Record<Confidence, string> = {
  green: "bg-emerald-500 ring-emerald-100",
  yellow: "bg-amber-400 ring-amber-100",
  red: "bg-rose-500 ring-rose-100",
};

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
