"use client";

import { useDeferredValue, useMemo, useState } from "react";

import type { IndexEntry } from "@/lib/data";

function pagesLabel(e: IndexEntry): string {
  const parts = [
    ...e.ranges.map(([a, b]) => `${a}–${b}`),
    ...e.pages.map((p) => String(p)),
  ];
  return parts.join(", ");
}

export function IndexBrowser({ entries }: { entries: IndexEntry[] }) {
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query);

  const shown = useMemo(() => {
    const q = deferred.trim().toLowerCase();
    if (!q) return entries;
    const asPage = /^\d{1,3}$/.test(q) ? Number(q) : null;
    return entries.filter(
      (e) =>
        e.term.toLowerCase().includes(q) ||
        (asPage !== null && e.all_pages.includes(asPage)),
    );
  }, [entries, deferred]);

  return (
    <>
      <div className="filter">
        <input
          type="search"
          value={query}
          onChange={(ev) => setQuery(ev.target.value)}
          placeholder="見出し語で絞る(数字だけなら頁で引く)"
          aria-label="索引の絞り込み"
        />
        <span className="filter__count">
          {shown.length.toLocaleString("ja-JP")} / {entries.length.toLocaleString("ja-JP")} 項目
        </span>
      </div>

      {shown.length === 0 ? (
        <p className="empty">該当なし。</p>
      ) : (
        <ul className="entries">
          {shown.map((e) => (
            <li key={e.line} className={e.kind === "continuation" ? "sub" : undefined}>
              <span className="term">
                {e.kind === "continuation" && <span className="sub-mark">— </span>}
                {e.kind === "continuation" ? (e.subentry ?? e.headword) : e.term}
                {e.see && <span className="see"> → {e.see}</span>}
              </span>
              <span className="pages">{pagesLabel(e)}</span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
