"""辞書マッチのベースライン抽出器を、索引 gold(O-1b)で採点する。

SPEC §10 G-07 は「生徒モデルは**辞書マッチ + 正規表現のベースラインを上回る**」ことを
求めている。**先にその下限を測る。** 上回るべき相手を知らずに学習を始めても、
出た数字が良いのか悪いのか判断できない。

やること: 索引の見出し語を本文 1845 年版から素朴に文字列検索し、
出てきた頁を索引が指す頁と突き合わせる。LLM も学習も使わない。

    python -m etl.build_baseline
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

from etl import sources

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "f14.converted.html"
GOLD = ROOT / "data" / "index_gold.json"
OUT = ROOT / "data" / "baseline.json"

PAGE_RE = re.compile(r"\[page\]\s*(\d{1,4})|\[page\s+(\d{1,4})\]")
HEAD_RE = re.compile(r"^CHAPTER\s+([IVXL]+)\.?$", re.I)


def page_texts() -> dict[int, str]:
    """頁番号 → その頁の本文(章の範囲だけ)。"""
    src = SRC.read_text(encoding="utf-8", errors="replace")
    page = 0
    seq: list[tuple[str, int]] = []
    for block in re.findall(r"<p\b[^>]*>(.*?)</p>", src, flags=re.S | re.I):
        t = re.sub(r"<[^>]+>", " ", block)
        t = html.unescape(t)
        m = PAGE_RE.search(t)
        if m:
            page = int(m.group(1) or m.group(2))
            continue
        t = re.sub(r"\[page[^\]]*\]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        if t and not sources.JUNK_RE.match(t):
            seq.append((t, page))

    heads = [i for i, (t, _) in enumerate(seq) if HEAD_RE.match(t.strip())]
    body = heads[-21:]
    ends = [i for i, (t, _) in enumerate(seq) if t.strip().rstrip(".").upper() == "INDEX"]
    tail = next((i for i in ends if i > body[-1]), len(seq))

    pages: dict[int, list[str]] = {}
    for t, p in seq[body[0] : tail]:
        if p > 0:
            pages.setdefault(p, []).append(t)
    return {p: " ".join(v) for p, v in pages.items()}


def norm(s: str) -> str:
    """照合用。合字・アクセントを潰し、小文字にして空白を畳む。"""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("æ", "ae").replace("Æ", "AE").replace("œ", "oe")
    return re.sub(r"\s+", " ", s.lower()).strip()


def search_term(term: str, pages: dict[int, str]) -> set[int]:
    """素朴な文字列検索。語境界だけ見て、活用も同義語も扱わない。"""
    t = norm(term)
    if len(t) < 3:
        return set()
    pat = re.compile(r"\b" + re.escape(t) + r"\b")
    return {p for p, text in pages.items() if pat.search(text)}


# 索引の見出し語には二つの型がある(実測 2026-09-05)。
# 「Bahia」「Amblyrhynchus」のような**名前**と、
# 「Absence of trees in Pampas」のような**編者が書いた説明文**である。
# 後者は本文にその文字列として存在しないので、文字列検索では原理的に当たらない。
FUNCTION_WORD = re.compile(r"\b(of|in|on|at|from|near|and|the|common|habits?|account)\b", re.I)


def headword_kind(h: str) -> str:
    return "description" if (len(h.split()) >= 3 and FUNCTION_WORD.search(h)) else "name"


def build() -> dict:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    pages = {p: norm(t) for p, t in page_texts().items()}

    rows = []
    for e in gold["entries"]:
        want = set(e["all_pages"])
        if not want:
            continue
        # 見出し語だけで引く(下位項目は語ではなく説明文なので使わない)
        found = search_term(e["headword"], pages)
        rows.append(
            {
                "line": e["line"],
                "headword": e["headword"],
                "gold_pages": sorted(want),
                "found_pages": sorted(found),
                "hit": sorted(want & found),
                "found_any": bool(want & found),
                "searchable": len(norm(e["headword"])) >= 3,
                "kind": headword_kind(e["headword"]),
            }
        )

    searchable = [r for r in rows if r["searchable"]]
    gold_total = sum(len(r["gold_pages"]) for r in searchable)
    hit_total = sum(len(r["hit"]) for r in searchable)
    found_total = sum(len(r["found_pages"]) for r in searchable)

    return {
        "schema": "beagle-atlas/baseline@1",
        "purpose": (
            "SPEC §10 G-07 が要求する下限。辞書マッチ + 正規表現がどこまで届くかを、"
            "学習を始める前に測っておく。"
        ),
        "method": (
            "索引の見出し語を、1845 年版本文の各頁に対して語境界つきの素朴な文字列検索で当てる。"
            "活用・同義語・綴りの揺れは一切扱わない。"
        ),
        "totals": {
            "entries": len(rows),
            "searchable_entries": len(searchable),
            "too_short_to_search": len(rows) - len(searchable),
            "gold_page_refs": gold_total,
            "found_page_refs": found_total,
            "hits": hit_total,
            "recall": round(hit_total / gold_total, 4) if gold_total else None,
            "precision": round(hit_total / found_total, 4) if found_total else None,
            "entries_with_any_hit": sum(1 for r in searchable if r["found_any"]),
            "entry_level_recall": (
                round(sum(1 for r in searchable if r["found_any"]) / len(searchable), 4)
                if searchable
                else None
            ),
        },
        "by_kind": {
            k: {
                "entries": len(sub),
                "gold_page_refs": sum(len(r["gold_pages"]) for r in sub),
                "hits": sum(len(r["hit"]) for r in sub),
                "recall": (
                    round(
                        sum(len(r["hit"]) for r in sub)
                        / sum(len(r["gold_pages"]) for r in sub),
                        4,
                    )
                    if sum(len(r["gold_pages"]) for r in sub)
                    else None
                ),
                "entry_level_recall": (
                    round(sum(1 for r in sub if r["found_any"]) / len(sub), 4) if sub else None
                ),
            }
            for k, sub in (
                (kind, [r for r in searchable if r["kind"] == kind])
                for kind in ("name", "description")
            )
        },
        "finding": (
            "索引の見出し語の約 4 分の 1 は、編者が書いた説明文であって本文中の文字列ではない。"
            "文字列検索では原理的に当たらないので、索引を再現率の物差しに使うときは"
            "**名前の型に限る**必要がある。"
        ),
        "entries": rows,
    }


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    t = d["totals"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  索引項目 {t['entries']:,}(検索可 {t['searchable_entries']:,} / 短すぎ {t['too_short_to_search']})")
    print(f"  頁参照 gold {t['gold_page_refs']:,} / 検索が出した {t['found_page_refs']:,} / 一致 {t['hits']:,}")
    print(f"  再現率 {t['recall']} / 適合率 {t['precision']}")
    print(f"  1 頁でも当てられた項目 {t['entries_with_any_hit']:,}({t['entry_level_recall']})")


if __name__ == "__main__":
    main()
