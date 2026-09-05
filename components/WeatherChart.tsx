import { readFileSync } from "node:fs";
import { join } from "node:path";

export type Weather = {
  source: { name: string; note: string };
  totals: {
    records: number;
    months_with_table: number;
    meteorological_tables: number;
    meteorological_tables_unread: string[];
    first_date: string;
    last_date: string;
    air_readings: number;
    water_readings: number;
    air_min_f: number;
    air_max_f: number;
    water_min_f: number;
    water_max_f: number;
  };
  monthly: {
    month: string;
    air_mean_f: number | null;
    water_mean_f: number | null;
    n_air: number;
    n_water: number;
  }[];
};

export function getWeather(): Weather {
  return JSON.parse(
    readFileSync(join(process.cwd(), "data", "weather.json"), "utf-8"),
  ) as Weather;
}

/** 気温と水温の月平均。標準的な集計であり、主張ではない。 */
export function WeatherChart({ w }: { w: Weather }) {
  const rows = w.monthly;
  const W = 1000;
  const H = 170;
  // 目盛は 10°F 刻みで、データの上下を含む範囲に取る
  const vals = rows.flatMap((r) => [r.air_mean_f, r.water_mean_f]).filter((v): v is number => v !== null);
  const lo = Math.floor(Math.min(...vals) / 10) * 10;
  const hi = Math.ceil(Math.max(...vals) / 10) * 10;
  const y = (v: number) => H - ((v - lo) / (hi - lo)) * H;
  const x = (i: number) => (i / Math.max(rows.length - 1, 1)) * W;

  const line = (key: "air_mean_f" | "water_mean_f") => {
    const seg: string[] = [];
    let open = false;
    rows.forEach((r, i) => {
      const v = r[key];
      if (v === null) {
        open = false;
        return;
      }
      seg.push(`${open ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`);
      open = true;
    });
    return seg.join("");
  };

  const ticks: number[] = [];
  for (let v = lo; v <= hi; v += 10) ticks.push(v);
  const years = rows
    .map((r, i) => ({ i, year: r.month.slice(0, 4), isJan: r.month.endsWith("-01") }))
    .filter((t) => t.isJan);

  return (
    <div className="scroll">
      <svg
        viewBox={`-30 -18 ${W + 46} ${H + 62}`}
        className="weather"
        role="img"
        aria-label={`気温と水温の月平均。${w.totals.first_date} から ${w.totals.last_date} まで`}
      >
        {ticks.map((v) => (
          <g key={v}>
            <line x1={0} y1={y(v)} x2={W} y2={y(v)} className="grat" />
            <text x={-4} y={y(v) + 3} className="gratlabel2" textAnchor="end">
              {v}°F
            </text>
          </g>
        ))}
        {years.map((t) => (
          <g key={t.year}>
            <line x1={x(t.i)} y1={-14} x2={x(t.i)} y2={H} className="chapline" />
            <text x={x(t.i) + 3} y={-6} className="chaplabel">
              {t.year}
            </text>
          </g>
        ))}
        <path d={line("air_mean_f")} fill="none" stroke="var(--land)" strokeWidth={1.8} />
        <path d={line("water_mean_f")} fill="none" stroke="var(--sea)" strokeWidth={1.8} />
        <text x={0} y={H + 18} className="gratlabel2">
          <tspan fill="var(--land)">気温</tspan> と <tspan fill="var(--sea)">水温</tspan>
          {" "}の月平均(華氏)。線が切れている月は、その観測が表に無い
        </text>
        <text x={0} y={H + 32} className="gratlabel2">
          {w.totals.first_date} 〜 {w.totals.last_date} / 気温 {w.totals.air_readings.toLocaleString("ja-JP")} 件・水温 {w.totals.water_readings.toLocaleString("ja-JP")} 件
        </text>
      </svg>
    </div>
  );
}
