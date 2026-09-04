// data/*.json を読む。画面は必ずここを通し、**数値を画面側に決め打ちしない**(SPEC G-11)。
import { readFileSync } from "node:fs";
import { join } from "node:path";

const DATA = join(process.cwd(), "data");

function read<T>(name: string): T {
  return JSON.parse(readFileSync(join(DATA, name), "utf-8")) as T;
}

export type ChapterAgreement = {
  chapter: number;
  words_a: number;
  words_b: number;
  sequence: number;
  multiset: number;
  passes_gate: boolean;
};

export type LedgerEntry = {
  id: string;
  side: string;
  where: string;
  observed: string;
  expected: string;
  handling: string;
};

export type Collation = {
  work: {
    title: string;
    author: string;
    edition: string;
    publisher: string;
    year: number;
    freeman: string;
    copyright_status: string;
  };
  sources: Record<string, { role: string; name: string; sha256: string }>;
  gate: { id: string; measure: string; threshold: number; note: string };
  totals: {
    chapters: number;
    paragraphs_a: number;
    paragraphs_b: number;
    typographic_residue_removed_a: number;
    words_all_a: number;
    words_all_b: number;
    words_body_a: number;
    words_body_b: number;
    words_outside_chapters_a: number;
    words_outside_chapters_b: number;
    sequence_median: number;
    sequence_min: number;
    multiset_median: number;
    multiset_min: number;
  };
  chapters: ChapterAgreement[];
  anomalies_detected: { ordinal: number; roman: string; paragraph: number }[];
  ledger: LedgerEntry[];
};

export type IndexEntry = {
  line: number;
  kind: "headword" | "continuation";
  headword: string;
  subentry: string | null;
  term: string;
  pages: number[];
  ranges: number[][];
  all_pages: number[];
  see: string | null;
};

export type IndexGold = {
  source: { name: string; sha256: string; copyright_status: string };
  provenance: string;
  boundaries: { start_marker: string; end_marker: string; note: string };
  counts: {
    entries: number;
    headwords: number;
    continuations: number;
    distinct_headwords: number;
    entries_with_ranges: number;
    cross_references: number;
    page_refs_expanded: number;
    pages_covered: number;
  };
  checks: {
    book_page_bounds: number[];
    out_of_range_refs: number[][];
    first_letter_inversions: string[][];
    inversion_note: string;
  };
  entries: IndexEntry[];
};

export const getCollation = (): Collation => read<Collation>("collation.json");
export const getIndexGold = (): IndexGold => read<IndexGold>("index_gold.json");
