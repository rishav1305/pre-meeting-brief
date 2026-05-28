// Hand-authored architecture diagram for the v2 pipeline.
// Colors:
//  SLATE  (deterministic) — fill #f1f5f9 stroke #64748b text #0f172a
//  PURPLE (agentic)       — fill #f3e8ff stroke #7c3aed text #5b21b6
//  TEAL   (MCP boundary)  — fill #ccfbf1 stroke #0d9488 text #0f766e

type BoxProps = {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  caption?: string;
  variant: "slate" | "purple" | "teal";
};

const VARIANTS = {
  slate: { fill: "#f1f5f9", stroke: "#64748b", text: "#0f172a" },
  purple: { fill: "#f3e8ff", stroke: "#7c3aed", text: "#5b21b6" },
  teal: { fill: "#ccfbf1", stroke: "#0d9488", text: "#0f766e" },
};

function Box({ x, y, w, h, label, caption, variant }: BoxProps) {
  const v = VARIANTS[variant];
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={6}
        ry={6}
        fill={v.fill}
        stroke={v.stroke}
        strokeWidth={1.5}
      />
      <text
        x={x + w / 2}
        y={y + (caption ? h / 2 - 2 : h / 2 + 4)}
        textAnchor="middle"
        fontSize={13}
        fontWeight={600}
        fill={v.text}
      >
        {label}
      </text>
      {caption && (
        <text
          x={x + w / 2}
          y={y + h / 2 + 14}
          textAnchor="middle"
          fontSize={10}
          fill={v.text}
          opacity={0.75}
        >
          {caption}
        </text>
      )}
    </g>
  );
}

export function ArchitectureSvg() {
  return (
    <svg
      viewBox="0 0 800 560"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Pre-meeting brief v2 architecture diagram"
      className="w-full"
    >
      <defs>
        <marker
          id="arrowhead"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M0,0 L10,5 L0,10 z" fill="#475569" />
        </marker>
      </defs>

      {/* Row 1 — triggers */}
      <Box x={50} y={20} w={140} h={50} label="Vercel Cron" variant="slate" />
      <Box x={210} y={20} w={200} h={50} label="Manual trigger (admin)" variant="slate" />

      {/* Triggers -> Qualification (converging arrows) */}
      <line
        x1={120}
        y1={70}
        x2={360}
        y2={110}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />
      <line
        x1={310}
        y1={70}
        x2={400}
        y2={110}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />

      {/* Row 2 — Qualification Agent */}
      <Box
        x={280}
        y={110}
        w={240}
        h={50}
        label="Qualification Agent"
        caption="judges: first meeting in 3mo?"
        variant="purple"
      />

      {/* Qualification -> resolve_company */}
      <line
        x1={400}
        y1={175}
        x2={400}
        y2={200}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />

      {/* Row 3 — resolve_company */}
      <Box
        x={280}
        y={200}
        w={240}
        h={50}
        label="resolve_company"
        caption="normalize domain, open run log"
        variant="slate"
      />

      {/* resolve_company -> orchestrator */}
      <line
        x1={400}
        y1={265}
        x2={400}
        y2={290}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />

      {/* Row 4 — Orchestrator */}
      <Box
        x={280}
        y={290}
        w={240}
        h={50}
        label="Orchestrator (LangGraph)"
        caption="state: BriefState"
        variant="slate"
      />

      {/* Orchestrator -> fan-out (4 boxes below) */}
      <line
        x1={400}
        y1={355}
        x2={400}
        y2={370}
        stroke="#475569"
        strokeWidth={1.5}
      />
      <line x1={110} y1={370} x2={690} y2={370} stroke="#475569" strokeWidth={1.5} />
      <line
        x1={110}
        y1={370}
        x2={110}
        y2={380}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />
      <line
        x1={305}
        y1={370}
        x2={305}
        y2={380}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />
      <line
        x1={500}
        y1={370}
        x2={500}
        y2={380}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />
      <line
        x1={695}
        y1={370}
        x2={695}
        y2={380}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />

      {/* Row 5 — 4 worker boxes */}
      <Box
        x={20}
        y={380}
        w={180}
        h={80}
        label="Research Agent"
        caption="web_search loop, deep-dive"
        variant="purple"
      />
      <Box
        x={215}
        y={380}
        w={180}
        h={80}
        label="Source-fetch (MCP)"
        caption="specter / cb / pb / attio"
        variant="teal"
      />
      <Box
        x={410}
        y={380}
        w={180}
        h={80}
        label="Data Quality Agent"
        caption="rank flags by severity"
        variant="purple"
      />
      <Box
        x={605}
        y={380}
        w={180}
        h={80}
        label="Synthesis Agent"
        caption="draft -> critique -> revise"
        variant="purple"
      />

      {/* Worker boxes -> merge caption */}
      <line x1={110} y1={460} x2={110} y2={485} stroke="#475569" strokeWidth={1.5} />
      <line x1={305} y1={460} x2={305} y2={485} stroke="#475569" strokeWidth={1.5} />
      <line x1={500} y1={460} x2={500} y2={485} stroke="#475569" strokeWidth={1.5} />
      <line x1={695} y1={460} x2={695} y2={485} stroke="#475569" strokeWidth={1.5} />
      <line x1={110} y1={485} x2={695} y2={485} stroke="#475569" strokeWidth={1.5} />
      <line
        x1={400}
        y1={485}
        x2={400}
        y2={500}
        stroke="#475569"
        strokeWidth={1.5}
        markerEnd="url(#arrowhead)"
      />
      <text
        x={400}
        y={520}
        textAnchor="middle"
        fontSize={12}
        fontWeight={600}
        fill="#0f172a"
      >
        merge_canonical &rarr; render &rarr; distribution
      </text>

      {/* Legend (bottom right) */}
      <g transform="translate(20, 530)">
        <rect x={0} y={0} width={12} height={12} rx={2} fill="#f3e8ff" stroke="#7c3aed" />
        <text x={18} y={10} fontSize={10} fill="#0f172a">
          Agentic
        </text>
        <rect x={80} y={0} width={12} height={12} rx={2} fill="#f1f5f9" stroke="#64748b" />
        <text x={98} y={10} fontSize={10} fill="#0f172a">
          Deterministic
        </text>
        <rect x={180} y={0} width={12} height={12} rx={2} fill="#ccfbf1" stroke="#0d9488" />
        <text x={198} y={10} fontSize={10} fill="#0f172a">
          MCP server
        </text>
      </g>
    </svg>
  );
}
