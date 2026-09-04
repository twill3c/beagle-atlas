// data/voyage.json を読み、地図と年表が使える形に整える。
// 数値は必ずここを通し、ページ側に決め打ちしない(SPEC G-11)。
import { readFileSync } from "node:fs";
import { join } from "node:path";

export type VoyageDay = {
  day: number;
  date: string;
  state: "Sea" | "Harbour" | "Land";
  lat: number | null;
  lon: number | null;
};

export type Voyage = {
  provenance: { source_id: string; citation: string; note: string };
  totals: {
    days: number;
    first_date: string;
    last_date: string;
    by_state: Record<string, number>;
    by_state_pct: Record<string, number>;
    days_with_coord: number;
    calendar_gaps: { from: string; to: string }[];
    speed_limit_km_per_day: number;
    speed_outliers: { day: number; date: string; lat: number; lon: number }[];
    speed_bad_legs: {
      from_day: number;
      to_day: number;
      from_date: string;
      to_date: string;
      km: number;
      days: number;
      km_per_day: number;
    }[];
  };
  days: VoyageDay[];
};

export const STATES = ["Sea", "Harbour", "Land"] as const;
export type State = (typeof STATES)[number];

export const STATE_JA: Record<State, string> = {
  Sea: "海上",
  Harbour: "停泊",
  Land: "上陸",
};

export function getVoyage(): Voyage {
  return JSON.parse(
    readFileSync(join(process.cwd(), "data", "voyage.json"), "utf-8"),
  ) as Voyage;
}

/** 経度を連続にほどく。西回りの一周なので、±180 をまたいだら以後 360 を引く。 */
export function unwrapTrack(days: VoyageDay[]) {
  const pts = days.filter((d) => d.lat !== null && d.lon !== null);
  let shift = 0;
  let prev: number | null = null;
  return pts.map((d) => {
    const raw = d.lon as number;
    if (prev !== null && raw - prev > 180) shift -= 360;
    else if (prev !== null && raw - prev < -180) shift += 360;
    prev = raw;
    return { day: d.day, date: d.date, state: d.state as State, lat: d.lat as number, x: raw + shift };
  });
}

/** 同じ区分が続く区間にまとめる(年表の帯を 1,740 本の矩形にしないため)。 */
export function stateRuns(days: VoyageDay[]) {
  const runs: { state: State; from: number; to: number; fromDate: string; toDate: string }[] = [];
  for (const d of days) {
    const last = runs[runs.length - 1];
    if (last && last.state === d.state && d.day === last.to + 1) {
      last.to = d.day;
      last.toDate = d.date;
    } else {
      runs.push({
        state: d.state as State,
        from: d.day,
        to: d.day,
        fromDate: d.date,
        toDate: d.date,
      });
    }
  }
  return runs;
}

/** 年ごとの区切り(年表の目盛)。 */
export function yearTicks(days: VoyageDay[]) {
  const seen = new Set<string>();
  const ticks: { year: string; day: number }[] = [];
  for (const d of days) {
    const y = d.date.slice(0, 4);
    if (!seen.has(y)) {
      seen.add(y);
      ticks.push({ year: y, day: d.day });
    }
  }
  return ticks;
}
