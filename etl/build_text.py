"""本文を段落単位で取り出し、安定した ID を振る(SPEC F-07 の土台)。

底本は 1845 年第 2 版(パブリックドメイン)。単位は **S-B の論理段落**を使う ——
S-A の `<p>` は頁で分断されるので段落の単位にならない(SPEC L0-4)。

章の頭は三行の決まった形をしている: `CHAPTER n` / 章題 / `--` 区切りの要約行。
この三つは本文段落に数えない(要約行は O-1a のオラクルとして別に使う)。

ID は `c01p001` の形。**訳はこの ID に紐づけるので、後から動かしてはならない。**

    python -m etl.build_text
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from etl import sources

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "pg944.body.txt"
OUT = ROOT / "data" / "text.json"

CHAPTER_LINE = re.compile(r"^CHAPTER\s+[IVXL]+\.?$", re.I)
SUMMARY_SEP = re.compile(r"--|—")


def build() -> dict:
    paras = sources.load_gutenberg(SRC)
    spans, _ = sources.chapter_spans(paras)

    chapters = []
    body_total = 0
    for n in range(1, sources.N_CHAPTERS + 1):
        a, b = spans[n]
        block = paras[a:b]
        if not CHAPTER_LINE.match(block[0].strip()):
            raise ValueError(f"第 {n} 章の先頭が章見出しでない: {block[0][:40]!r}")
        title = block[1].strip()
        # 要約行は `--` で区切られた話題の列。章題の次にある
        summary_idx = next(
            (i for i in (2, 3) if i < len(block) and len(SUMMARY_SEP.findall(block[i])) >= 2),
            None,
        )
        if summary_idx is None:
            raise ValueError(f"第 {n} 章の要約行が見つからない")
        body = block[summary_idx + 1 :]
        items = [
            {
                "id": f"c{n:02d}p{i:03d}",
                "chapter": n,
                "seq": i,
                "words": len(sources.norm_words(t)),
                "text": t,
            }
            for i, t in enumerate(body, 1)
        ]
        body_total += len(items)
        chapters.append(
            {
                "chapter": n,
                "title": title,
                "summary": block[summary_idx],
                "paragraphs": len(items),
                "words": sum(x["words"] for x in items),
                "items": items,
            }
        )

    return {
        "schema": "beagle-atlas/text@1",
        "source": {
            "id": "S-B",
            "work": "Darwin, Journal of Researches, 2nd ed. (London: John Murray, 1845)",
            "copyright_status": "public domain",
            "unit": "S-B の論理段落。S-A の <p> は頁で分断されるので単位にならない",
        },
        "totals": {
            "chapters": len(chapters),
            "paragraphs": body_total,
            "words": sum(c["words"] for c in chapters),
        },
        "chapters": chapters,
    }


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    t = d["totals"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  {t['chapters']} 章 / 本文段落 {t['paragraphs']:,} / 語 {t['words']:,}")
    for c in d["chapters"][:3]:
        print(f"    第 {c['chapter']:>2} 章 {c['paragraphs']:>3} 段落 {c['words']:>6,} 語  {c['title'][:40]}")


if __name__ == "__main__":
    main()
