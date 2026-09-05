// data/figures.json を読む。数値はここを通し、ページ側に決め打ちしない(SPEC G-11)。
import { readFileSync } from "node:fs";
import { join } from "node:path";

export type PageRef = { page: number; refs: number };
export type ChapterRefs = {
  chapter: number;
  page_from: number;
  page_to: number;
  pages: number;
  refs: number;
  refs_per_page: number;
};
export type MonthRow = {
  month: string;
  Sea: number;
  Harbour: number;
  Land: number;
  days: number;
};

export type Figures = {
  note: string;
  index_density: {
    page_from: number;
    page_to: number;
    total_refs_in_body: number;
    refs_outside_body: number;
    max_refs_on_a_page: number;
    pages_with_no_ref: number;
    by_page: PageRef[];
    by_chapter: ChapterRefs[];
  };
  voyage_monthly: { months: number; first: string; last: string; rows: MonthRow[] };
};

export function getFigures(): Figures {
  return JSON.parse(
    readFileSync(join(process.cwd(), "data", "figures.json"), "utf-8"),
  ) as Figures;
}
