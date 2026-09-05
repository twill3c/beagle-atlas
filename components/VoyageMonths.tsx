import type { Figures } from "@/lib/figures";

const COLOR = { Sea: "var(--sea)", Harbour: "var(--harbour)", Land: "var(--land)" } as const;
const ORDER = ["Sea", "Harbour", "Land"] as const;

/** 1,740 日を月ごとに三区分で積む。標準的な内訳であり、主張ではない。 */
export function VoyageMonths({ fig }: { fig: Figures["voyage_monthly"] }) {
  const W = 1000;
  const H = 130;
  const rows = fig.rows;
  const bw = W / rows.length;
  const max = Math.max(...rows.map((r) => r.days));

  return (
    <div className="scroll">
      <svg
        viewBox={`0 -16 ${W} ${H + 40}`}
        className="months"
        role="img"
        aria-label={`航海の月別内訳。${fig.first} から ${fig.last} まで ${fig.months} か月`}
      >
        {rows.map((r, i) => {
          let y = H;
          return (
            <g key={r.month}>
              {ORDER.map((s) => {
                const h = (r[s] / max) * H;
                y -= h;
                return (
                  <rect
                    key={s}
                    x={i * bw + 0.5}
                    y={y}
                    width={Math.max(bw - 1, 0.8)}
                    height={h}
                    fill={COLOR[s]}
                  />
                );
              })}
            </g>
          );
        })}
        {rows.map((r, i) =>
          r.month.endsWith("-01") ? (
            <g key={`t${r.month}`}>
              <line x1={i * bw} y1={-12} x2={i * bw} y2={H + 3} className="chapline" />
              <text x={i * bw + 3} y={-5} className="chaplabel">
                {r.month.slice(0, 4)}
              </text>
            </g>
          ) : null,
        )}
        <line x1={0} y1={H} x2={W} y2={H} className="axis" />
        <text x={0} y={H + 16} className="gratlabel2">
          1 本が 1 か月({fig.first} 〜 {fig.last})。高さはその月の日数、色は海上・停泊・上陸
        </text>
      </svg>
    </div>
  );
}
