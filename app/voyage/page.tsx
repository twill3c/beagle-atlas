import { STATES, STATE_JA, getVoyage, stateRuns, unwrapTrack, yearTicks } from "@/lib/voyage";
import type { State } from "@/lib/voyage";

export const metadata = {
  title: "航路と年表 — ビーグル・アトラス",
  description:
    "ビーグル号の 1,740 日を、海上・停泊・上陸の三区分で一枚に置く。事前登録した主張が落ちた記録つき。",
};

const COLOR: Record<State, string> = {
  Sea: "var(--sea)",
  Harbour: "var(--harbour)",
  Land: "var(--land)",
};

export default function VoyagePage() {
  const v = getVoyage();
  const track = unwrapTrack(v.days);
  const runs = stateRuns(v.days);
  const allTicks = yearTicks(v.days);
  const t = v.totals;

  // --- 地図(正距円筒。経度はほどいてあるので太平洋横断が一本になる)
  const xs = track.map((p) => p.x);
  const ys = track.map((p) => -p.lat);
  const x0 = Math.floor(Math.min(...xs) / 30) * 30;
  const x1 = Math.ceil(Math.max(...xs) / 30) * 30;
  const y0 = Math.floor(Math.min(...ys) / 15) * 15;
  const y1 = Math.ceil(Math.max(...ys) / 15) * 15;
  // 端のラベルが切れないための余白(度)。左は緯度ラベル(「50°N」で 4 文字)が
  // 内側から外へ伸びるので広く取る —— 実測 14 では切れた(2026-09-05・目視で発見)
  const PAD_L = 30;
  const PAD = 14;
  const vb = `${x0 - PAD_L} ${y0 - PAD} ${x1 - x0 + PAD_L + PAD} ${y1 - y0 + PAD * 2}`;

  // 区分ごとに線を組む。座標が 5 日以上とんだところと、
  // 帆走の物理限界(SPEC G-06)を超える区間では線を切る
  const badLegs = new Set(t.speed_bad_legs.map((l) => l.from_day));
  const paths: Record<State, string[]> = { Sea: [], Harbour: [], Land: [] };
  for (let i = 0; i < track.length - 1; i++) {
    const a = track[i];
    const b = track[i + 1];
    if (b.day - a.day > 5 || badLegs.has(a.day)) continue;
    paths[a.state].push(`M${a.x.toFixed(2)} ${(-a.lat).toFixed(2)}L${b.x.toFixed(2)} ${(-b.lat).toFixed(2)}`);
  }

  const lonLines: number[] = [];
  for (let x = x0; x <= x1; x += 30) lonLines.push(x);
  const latLines: number[] = [];
  for (let y = y0; y <= y1; y += 15) latLines.push(y);
  const lonLabel = (x: number) => {
    const w = (((x + 180) % 360) + 360) % 360 - 180; // ほどいた経度を実際の値に戻す
    return w === 0 ? "0°" : `${Math.abs(w)}°${w > 0 ? "E" : "W"}`;
  };
  const latLabel = (y: number) => (y === 0 ? "0°" : `${Math.abs(y)}°${y > 0 ? "S" : "N"}`);

  // --- 年表(1,740 日を帯に)
  const W = 1000;
  const H = 34;
  const px = (day: number) => ((day - 1) / t.days) * W;

  // 目盛は「直前に**残した**もの」との間隔で間引く。元の配列を見ると、
  // 4 日しかない 1831 年が残って 1832 年が落ちる(2026-09-05・目視で発見)
  const ticks = allTicks.reduce<typeof allTicks>((kept, tk) => {
    const last = kept[kept.length - 1];
    if (!last || px(tk.day) - px(last.day) > W * 0.03) kept.push(tk);
    else kept[kept.length - 1] = tk; // 近すぎたら、後の年の方を残す
    return kept;
  }, []);

  return (
    <main>
      <h1>航路と年表</h1>
      <p className="lede">
        {t.first_date} から {t.last_date} までの {t.days.toLocaleString("ja-JP")} 日を、
        その日ビーグル号がどこにいたかで三つに分けて置いた。
        座標を持つのは {t.days_with_coord.toLocaleString("ja-JP")} 日。
      </p>

      <ul className="stats">
        {STATES.map((s) => (
          <li key={s}>
            <span className="k">
              <span className="swatch" style={{ background: COLOR[s] }} aria-hidden="true" />
              {STATE_JA[s]}
            </span>
            <span className="v">
              {t.by_state[s].toLocaleString("ja-JP")}
              <span className="u">日 / {t.by_state_pct[s].toFixed(1)}%</span>
            </span>
          </li>
        ))}
      </ul>

      <h2>航路</h2>
      <p>
        正距円筒図法。<strong>経度はほどいてあるので、太平洋の横断が一本の線になる</strong>
        (実際の航路は日付変更線を 1 度またぐ)。座標が 5 日以上とんだ区間は線を切ってある。
      </p>
      <div className="scroll">
        <svg viewBox={vb} className="map" role="img" aria-label="ビーグル号の航路">
          {lonLines.map((x) => (
            <line key={`v${x}`} x1={x} y1={y0} x2={x} y2={y1} className="grat" />
          ))}
          {latLines.map((y) => (
            <line key={`h${y}`} x1={x0} y1={y} x2={x1} y2={y} className={y === 0 ? "grat grat--eq" : "grat"} />
          ))}
          {lonLines.map((x) => (
            <text key={`vt${x}`} x={x} y={y1 + 9} className="gratlabel" textAnchor="middle">
              {lonLabel(x)}
            </text>
          ))}
          {latLines.map((y) => (
            <text key={`ht${y}`} x={x0 - 3} y={y + 2} className="gratlabel" textAnchor="end">
              {latLabel(y)}
            </text>
          ))}
          {STATES.map((s) => (
            <path key={s} d={paths[s].join("")} fill="none" stroke={COLOR[s]} strokeWidth={1.6}
              strokeLinecap="round" />
          ))}
        </svg>
      </div>

      <div className="note">
        <p style={{ marginTop: 0 }}>
          <strong>資料の座標には誤りが混じっている。</strong>
          帆船の物理限界(10 ノット = 1 日 {t.speed_limit_km_per_day.toLocaleString("ja-JP")} km)を
          超える区間が <strong>{t.speed_bad_legs.length} 件</strong>あった。
          いちばん極端なものは 1 日で {Math.max(...t.speed_bad_legs.map((l) => l.km_per_day)).toLocaleString("ja-JP")} km 進むことになる。
        </p>
        <p style={{ marginBottom: 0 }}>
          そのうち {t.speed_outliers.length} 件は<strong>前後の両方に対して外れる</strong>ので、
          点そのものの誤記と判る({t.speed_outliers.map((o) => o.date).join("・")} ——
          前後の経度が 50°W 台なのに、この日だけ 5°W 台になっている)。
          残りは階段状のずれで、どちらの点が誤りかを決められない。
          <strong>どれも消さずに数え、地図では線を繋がないだけにしてある。</strong>
        </p>
      </div>

      <h2>年表</h2>
      <p>
        左から右へ 1 日ずつ。{runs.length.toLocaleString("ja-JP")} 本の連続区間にまとめてある。
      </p>
      <div className="scroll">
        <svg viewBox={`0 -12 ${W} ${H + 24}`} className="ribbon" role="img" aria-label="航海の年表">
          {runs.map((r) => (
            <rect key={r.from} x={px(r.from)} y={0} width={Math.max(px(r.to + 1) - px(r.from), 0.4)}
              height={H} fill={COLOR[r.state]} />
          ))}
          {/* 近すぎる目盛はラベルが重なるので落とす。1831 年は 4 日しか無く、
              1832 年の目盛と 0.2% しか離れていない(2026-09-05・目視で発見) */}
          {ticks.map((tk) => (
            <g key={tk.year}>
              <line x1={px(tk.day)} y1={-4} x2={px(tk.day)} y2={H + 4} className="tick" />
              <text x={px(tk.day) + 4} y={-4} className="ticklabel">{tk.year}</text>
            </g>
          ))}
        </svg>
      </div>

      <h2>事前登録した主張は落ちた</h2>
      <div className="note note--warn">
        <p style={{ marginTop: 0 }}>
          このデータを取る前に、こう書いて登録していた ——
          <strong>「『ビーグル号航海記』は航海の本ではない。陸にいた日が過半(55% 以上)である」</strong>。
        </p>
        <p>
          実測は <strong>{t.by_state_pct.Land.toFixed(1)}%</strong>。近くもない。
          閾値は資料を取る前に置いた値なので、<strong>取得後に動かさず、主張の方を降ろした</strong>。
        </p>
        <p style={{ marginBottom: 0 }}>
          ただし読み方には含みがある。この区分は<strong>夜をどこで過ごしたか</strong>で、
          昼に上陸して夜は船に戻った日は停泊({t.by_state_pct.Harbour.toFixed(1)}%)の側に入る。
          昼を基準にすれば別の数になる —— が、
          <strong>主張を救うために物差しを取り替えるのは筋が悪い</strong>ので、そうしない。
        </p>
      </div>

      <h2>この数字の出どころ</h2>
      <p className="small">
        {v.provenance.citation}
        <br />
        {v.provenance.note}
      </p>
      <p className="small">
        暦日の飛びは {t.calendar_gaps.length} 箇所
        {t.calendar_gaps.map((g) => `(${g.from} → ${g.to})`).join("")} ——
        日付変更線を西へ越えたことによるもので、資料の記述とも一致する。
      </p>
    </main>
  );
}
