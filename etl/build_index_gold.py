"""索引を抽出器の gold(O-1b)として書き出す。

出力は `data/index_gold.json`。決定的(同一入力なら bit 一致)であること。
底本の sha256 を刻んで、どの翻刻から作った gold かを後から辿れるようにする。

    python -m etl.build_index_gold
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from etl import index as idx
from etl import sources

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "raw" / "f14.converted.html"
OUT = ROOT / "data" / "index_gold.json"


def build() -> dict:
    paras, _dropped = sources.load_darwin_online(SOURCE)
    entries = idx.parse_index(paras)
    lo, hi = sources.book_page_bounds(SOURCE)

    out_of_range = idx.out_of_range_refs(entries, lo, hi)
    inversions = idx.first_letter_inversions(entries)

    records = [
        {
            "line": e.line,
            "kind": e.kind,
            "headword": e.headword,
            "subentry": e.subentry,
            "term": e.term,
            "pages": list(e.pages),
            "ranges": [list(r) for r in e.ranges],
            "all_pages": list(e.all_pages),
            "see": e.see,
        }
        for e in entries
    ]

    return {
        "schema": "beagle-atlas/index_gold@1",
        "source": {
            "id": "S-A",
            "name": "Darwin Online, Journal of Researches 2nd ed. (1845), F14",
            "file": SOURCE.name,
            "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "copyright_status": "public domain",
        },
        "provenance": (
            "1845 年版の巻末索引を機械的にパースしたもの。"
            "本プロジェクトも言語モデルも一行も書いていないため、抽出器の評価が循環しない(O-1b)。"
        ),
        "boundaries": {
            "start_marker": "INDEX.",
            "end_marker": "THE END.",
            "note": "終端は本が印刷している。以降は印刷所の奥付と出版社広告。",
        },
        "counts": {
            "entries": len(records),
            "headwords": sum(1 for e in entries if e.kind == "headword"),
            "continuations": sum(1 for e in entries if e.kind == "continuation"),
            "distinct_headwords": len({e.headword for e in entries}),
            "entries_with_ranges": sum(1 for e in entries if e.ranges),
            "cross_references": sum(1 for e in entries if e.see),
            "page_refs_expanded": sum(len(e.all_pages) for e in entries),
            "pages_covered": len({p for e in entries for p in e.all_pages}),
        },
        "checks": {
            "book_page_bounds": [lo, hi],
            "out_of_range_refs": out_of_range,
            "first_letter_inversions": [list(p) for p in inversions],
            "inversion_note": (
                "('J','I') は 1845 年の組版に見られる I/J 合併配列によるもので、誤りではない。"
            ),
        },
        "entries": records,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    c = data["counts"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  項目 {c['entries']:,}(見出し {c['headwords']:,} / 継続 {c['continuations']:,})")
    print(f"  異なり見出し語 {c['distinct_headwords']:,} / 頁参照 {c['page_refs_expanded']:,}")
    print(f"  被覆頁数 {c['pages_covered']:,} / 頁範囲 {data['checks']['book_page_bounds']}")
    print(f"  範囲外の参照 {len(data['checks']['out_of_range_refs'])} 件")


if __name__ == "__main__":
    main()
