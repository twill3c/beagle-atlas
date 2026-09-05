"""標準図のためのデータを組む(SPEC §6 の路線 —— 主張は立てない)。

出すのは二つ。

1. **索引の頁密度**: 1845 年版の索引が、本のどの頁を何回指しているか。
   指したのは 1845 年の編者であって私たちではないので、これは
   「当時の人がどこを引くべきだと考えたか」の記録である。
2. **航海の月別内訳**: 1,740 日を月ごとに海上 / 停泊 / 上陸で分けたもの。

どちらも標準的な集計で、主張ではない。**図が何かを言っているように見えたら、
それは読む人が読み取ったのであって、こちらが主張したのではない**という位置づけ。

    python -m etl.build_figures
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path

from etl import sources

ROOT = Path(__file__).resolve().parents[1]
SRC_1845 = ROOT / "raw" / "f14.converted.html"
DATA = ROOT / "data"
OUT = DATA / "figures.json"

PAGE_RE = re.compile(r"\[page\]\s*(\d{1,4})|\[page\s+(\d{1,4})\]")
HEAD_RE = re.compile(r"^CHAPTER\s+([IVXL]+)\.?$", re.I)
N_CHAPTERS = 21


def chapter_page_ranges() -> dict[int, tuple[int, int]]:
    """1845 年版の各章が占める頁の範囲を、頁マーカーを追って決める。"""
    src = SRC_1845.read_text(encoding="utf-8", errors="replace")
    page = 0
    seq: list[tuple[str, int]] = []  # (段落テキスト, その時点の頁)
    for block in re.findall(r"<p\b[^>]*>(.*?)</p>", src, flags=re.S | re.I):
        text = re.sub(r"<[^>]+>", " ", block)
        text = html.unescape(text)
        m = PAGE_RE.search(text)
        if m:
            page = int(m.group(1) or m.group(2))
            continue
        text = re.sub(r"\[page[^\]]*\]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text and not sources.JUNK_RE.match(text):
            seq.append((text, page))

    heads = [i for i, (t, _) in enumerate(seq) if HEAD_RE.match(t.strip())]
    if len(heads) < N_CHAPTERS:
        raise ValueError(f"章見出しが {len(heads)} 件({N_CHAPTERS} 必要)")
    body = heads[-N_CHAPTERS:]
    ends = [i for i, (t, _) in enumerate(seq) if t.strip().rstrip(".").upper() == "INDEX"]
    tail = next((i for i in ends if i > body[-1]), len(seq))

    ranges: dict[int, tuple[int, int]] = {}
    for k in range(1, N_CHAPTERS + 1):
        a = body[k - 1]
        b = body[k] if k < N_CHAPTERS else tail
        pages = [p for _, p in seq[a:b] if p > 0]
        if not pages:
            raise ValueError(f"第 {k} 章に頁が付かない")
        ranges[k] = (min(pages), max(pages))

    # 検算: 章の頁範囲が順に並び、重なりが 1 頁以内(章の変わり目は同じ頁に載る)
    for k in range(1, N_CHAPTERS):
        if ranges[k + 1][0] < ranges[k][0]:
            raise ValueError(f"章の頁範囲が逆転: {k} {ranges[k]} → {k+1} {ranges[k+1]}")
    return ranges


def build() -> dict:
    gold = json.loads((DATA / "index_gold.json").read_text(encoding="utf-8"))
    voyage = json.loads((DATA / "voyage.json").read_text(encoding="utf-8"))

    # --- 図 1: 索引の頁密度
    per_page = Counter()
    for e in gold["entries"]:
        for p in e["all_pages"]:
            per_page[p] += 1
    ranges = chapter_page_ranges()
    body_lo = min(a for a, _ in ranges.values())
    body_hi = max(b for _, b in ranges.values())

    density = [
        {"page": p, "refs": per_page.get(p, 0)} for p in range(body_lo, body_hi + 1)
    ]
    total_refs = sum(d["refs"] for d in density)
    outside = sum(v for p, v in per_page.items() if not body_lo <= p <= body_hi)

    chapters = []
    for k, (a, b) in sorted(ranges.items()):
        refs = sum(per_page.get(p, 0) for p in range(a, b + 1))
        pages = b - a + 1
        chapters.append(
            {
                "chapter": k,
                "page_from": a,
                "page_to": b,
                "pages": pages,
                "refs": refs,
                "refs_per_page": round(refs / pages, 2),
            }
        )

    # --- 図 2: 航海の月別内訳
    months: dict[str, Counter] = {}
    for d in voyage["days"]:
        months.setdefault(d["date"][:7], Counter())[d["state"]] += 1
    monthly = [
        {
            "month": m,
            "Sea": c["Sea"],
            "Harbour": c["Harbour"],
            "Land": c["Land"],
            "days": sum(c.values()),
        }
        for m, c in sorted(months.items())
    ]
    if sum(m["days"] for m in monthly) != voyage["totals"]["days"]:
        raise ValueError("月別の合計が全日数と一致しない")

    return {
        "schema": "beagle-atlas/figures@1",
        "note": (
            "標準的な集計であり、主張ではない。索引が指した頁は 1845 年の編者が選んだもので、"
            "本サイトが選んだものではない。"
        ),
        "index_density": {
            "page_from": body_lo,
            "page_to": body_hi,
            "total_refs_in_body": total_refs,
            "refs_outside_body": outside,
            "max_refs_on_a_page": max(d["refs"] for d in density),
            "pages_with_no_ref": sum(1 for d in density if d["refs"] == 0),
            "by_page": density,
            "by_chapter": chapters,
        },
        "voyage_monthly": {
            "months": len(monthly),
            "first": monthly[0]["month"],
            "last": monthly[-1]["month"],
            "rows": monthly,
        },
    }


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    i = d["index_density"]
    v = d["voyage_monthly"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  索引密度: 本文 {i['page_from']}–{i['page_to']} 頁 / 参照 {i['total_refs_in_body']:,}"
          f" / 最大 {i['max_refs_on_a_page']} 件・無参照 {i['pages_with_no_ref']} 頁"
          f" / 本文外の参照 {i['refs_outside_body']}")
    print(f"  月別: {v['months']} か月 {v['first']}–{v['last']}")


if __name__ == "__main__":
    main()
