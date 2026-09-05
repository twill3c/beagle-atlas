import type { Figures } from "@/lib/figures";

/** 索引が本のどの頁を何回指しているか。指したのは 1845 年の編者である。 */
export function IndexDensity({ fig }: { fig: Figures["index_density"] }) {
  const W = 1000;
  const H = 150;
  const n = fig.by_page.length;
  const bw = W / n;
  const max = fig.max_refs_on_a_page;
  const x = (page: number) => ((page - fig.page_from) / n) * W;

  // 上端は章番号(y = -5)、下端は 2 行目の説明(y = H + 30)まで入れる。
  // 高さを H + 42 にすると下端が H + 26 になり、説明が切れる(2026-09-05・目視で発見)。
  // 左右にも余白を取る —— x=0 に置いた文字でも、字の左サイドベアリングぶん
  // わずかに外へ出る(狭い幅で 2.1 単位。HC-159 の検査が検出)
  const VIEWBOX = `-8 -16 ${W + 16} ${H + 52}`;

  return (
    <div className="scroll">
      <svg
        viewBox={VIEWBOX}
        className="density"
        role="img"
        aria-label={`索引の頁密度。${fig.page_from} 頁から ${fig.page_to} 頁まで、1 頁あたり最大 ${max} 件`}
      >
        {/* 章の境目 */}
        {fig.by_chapter.map((c) => (
          <g key={c.chapter}>
            <line x1={x(c.page_from)} y1={-12} x2={x(c.page_from)} y2={H} className="chapline" />
            <text x={x(c.page_from) + 2} y={-5} className="chaplabel">
              {c.chapter}
            </text>
          </g>
        ))}
        {/* 頁ごとの参照数 */}
        {fig.by_page.map((p) => (
          <rect
            key={p.page}
            x={x(p.page)}
            y={H - (p.refs / max) * H}
            width={Math.max(bw, 0.6)}
            height={(p.refs / max) * H}
            fill="var(--accent)"
          />
        ))}
        <line x1={0} y1={H} x2={W} y2={H} className="axis" />
        <text x={0} y={H + 14} className="gratlabel2">
          {fig.page_from} 頁
        </text>
        <text x={W} y={H + 14} className="gratlabel2" textAnchor="end">
          {fig.page_to} 頁
        </text>
        <text x={0} y={H + 30} className="gratlabel2">
          縦軸は 1 頁あたりの索引参照数(最大 {max} 件)。上の数字は 1845 年版の章番号
        </text>
      </svg>
    </div>
  );
}
