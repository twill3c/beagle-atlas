"""1839 年初版と 1845 年第 2 版の差分を測る(SPEC §6.0 / G-20a・G-20b・G-20c)。

**事前登録した測り方に従う**(SPEC §6.0。閾値は測定前に凍結してある):

- 章番号で対応づけない。1839 年版は 23 章、1845 年版は 21 章で 1:1 に対応しない
- 二版を整列し、1845 年版の各章に対応する 1839 年版の範囲を alignment から決める
- 「ガラパゴスを扱う範囲」は測定前に特定済み —— **1845 年版 第 17 章**
- 決定的(同一入力で bit 一致)であること

整列は**文の単位**で行う。語単位では系列が長すぎて実用にならず、段落単位では
Darwin Online の翻刻が頁で分断されるため単位にならない(SPEC L0-4)。

    python -m etl.edition_diff
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from etl import sources

ROOT = Path(__file__).resolve().parents[1]
SRC_1845 = ROOT / "raw" / "f14.converted.html"
SRC_1839 = ROOT / "raw" / "f10_3.converted.html"
OUT = ROOT / "data" / "edition_diff.json"

GALAPAGOS_CHAPTER = 17  # SPEC §6.0 で測定前に固定
HEAD_RE = re.compile(r"^CHAPTER\s+([IVXL]+)\.?$", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Sentence:
    text: str
    key: str
    words: int


def paragraphs(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for b in re.findall(r"<p\b[^>]*>(.*?)</p>", src, flags=re.S | re.I):
        t = re.sub(r"<[^>]+>", " ", b)
        t = html.unescape(t)
        t = re.sub(r"\[page[^\]]*\]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        if t and not sources.JUNK_RE.match(t):
            out.append(t)
    return out


def body_chapter_spans(paras: list[str], n_chapters: int) -> dict[int, tuple[int, int]]:
    """本文側の章 n 件の [start, end)。目次より後ろ(末尾 n 件)を採る。"""
    hits = [i for i, p in enumerate(paras) if HEAD_RE.match(p.strip())]
    if len(hits) < n_chapters:
        raise ValueError(f"章見出しが {len(hits)} 件({n_chapters} 必要)")
    body = hits[-n_chapters:]
    end_marks = [i for i, p in enumerate(paras) if p.strip().rstrip(".").upper() == "THE END"]
    tail = next((i for i in end_marks if i > body[-1]), len(paras))
    return {k: (body[k - 1], body[k] if k < n_chapters else tail) for k in range(1, n_chapters + 1)}


def sentences(paras: list[str]) -> list[Sentence]:
    out: list[Sentence] = []
    for p in paras:
        for s in SENT_SPLIT.split(p):
            s = s.strip()
            if not s:
                continue
            w = sources.norm_words(s)
            if not w:
                continue
            out.append(Sentence(text=s, key=" ".join(w), words=len(w)))
    return out


def build() -> dict:
    p45, p39 = paragraphs(SRC_1845), paragraphs(SRC_1839)
    sp45 = body_chapter_spans(p45, 21)
    sp39 = body_chapter_spans(p39, 23)

    # 章ごとの文を作り、通し番号で章に引けるようにする
    sent45: list[Sentence] = []
    chap_of45: list[int] = []
    for n in range(1, 22):
        a, b = sp45[n]
        s = sentences(p45[a:b])
        sent45 += s
        chap_of45 += [n] * len(s)

    sent39: list[Sentence] = []
    chap_of39: list[int] = []
    for n in range(1, 24):
        a, b = sp39[n]
        s = sentences(p39[a:b])
        sent39 += s
        chap_of39 += [n] * len(s)

    k45 = [s.key for s in sent45]
    k39 = [s.key for s in sent39]
    sm = SequenceMatcher(None, k39, k45, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 0]

    # 1845 年版の各章に、対応する 1839 年版の文の範囲を割り当てる。
    #
    # **一致した文の最小・最大だけで範囲を取ってはならない。** アンカーの疎な章は
    # 範囲が短く切られて比が跳ね上がり、隣の章が取りこぼしを吸って比が沈む。
    # 実測(2026-09-05)では第 9 章 2.32・第 20 章 2.30 に対し第 11 章 0.41・第 21 章 0.55 と
    # 極端に振れ、順位がアンカー密度の産物になっていた。
    #
    # そこで**分割**にする。章の境目は「章 n の最後のアンカーと章 n+1 の最初のアンカーの中点」。
    # こうすると 1839 年版の全文がちょうど一度ずつどこかの章に属し、総語数が保存される
    # (この保存は下で assert して確かめる)。
    lo: dict[int, int] = {}
    hi: dict[int, int] = {}
    matched_sents = 0
    for b in blocks:
        matched_sents += b.size
        for off in range(b.size):
            n = chap_of45[b.b + off]
            i39 = b.a + off
            lo[n] = min(lo.get(n, i39), i39)
            hi[n] = max(hi.get(n, i39), i39)

    anchored = sorted(lo)
    if len(anchored) < 21:
        raise ValueError(f"アンカーの無い章がある: {set(range(1, 22)) - set(anchored)}")
    bounds: dict[int, tuple[int, int]] = {}
    for idx, n in enumerate(anchored):
        start = 0 if idx == 0 else (hi[anchored[idx - 1]] + lo[n] + 1) // 2
        end = len(sent39) if idx == len(anchored) - 1 else (hi[n] + lo[anchored[idx + 1]] + 1) // 2
        bounds[n] = (start, end)

    words45_total = sum(s.words for s in sent45)
    words39_total = sum(s.words for s in sent39)

    rows = []
    for n in range(1, 22):
        w45 = sum(s.words for s, c in zip(sent45, chap_of45) if c == n)
        a, b = bounds[n]
        w39 = sum(s.words for s in sent39[a:b])
        rows.append(
            {
                "chapter_1845": n,
                "words_1845": w45,
                "words_1839_aligned": w39,
                "ratio": round(w45 / w39, 4) if w39 else None,
                "span_1839": [a, b],
                "anchor_span_1839": [lo[n], hi[n]],
                "anchors": sum(1 for i in range(a, b) if lo[n] <= i <= hi[n]),
                "chapters_1839": sorted({c for c in chap_of39[a:b]}),
            }
        )

    # 分割の検算: 1839 年版の語がちょうど一度ずつ数えられている
    partition_total = sum(r["words_1839_aligned"] for r in rows)
    if partition_total != words39_total:
        raise ValueError(
            f"分割が保存していない: 章別合計 {partition_total:,} ≠ 全体 {words39_total:,}"
        )
    if [r["span_1839"][0] for r in rows] != sorted(r["span_1839"][0] for r in rows):
        raise ValueError("章の境目が単調でない")

    ranked = sorted(
        [r for r in rows if r["ratio"] is not None], key=lambda r: r["ratio"], reverse=True
    )
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    gal = next(r for r in rows if r["chapter_1845"] == GALAPAGOS_CHAPTER)

    gates = {
        "G-20a": {
            "claim": "本文全体の語数が減る(1845 < 1839)",
            "measured": {"words_1845": words45_total, "words_1839": words39_total},
            "passes": words45_total < words39_total,
        },
        "G-20b": {
            "claim": "ガラパゴス範囲の語数が増える(比 > 1.00)",
            "measured": {"chapter": GALAPAGOS_CHAPTER, "ratio": gal["ratio"]},
            "passes": bool(gal["ratio"] and gal["ratio"] > 1.0),
        },
        "G-20c": {
            "claim": "その増加率が全範囲中で上位 3 位以内",
            "measured": {"rank": gal.get("rank"), "of": len(ranked)},
            "passes": bool(gal.get("rank") and gal["rank"] <= 3),
        },
    }

    return {
        "schema": "beagle-atlas/edition_diff@1",
        "preregistered": "SPEC §6.0(2026-09-05 登録。この計算より前に閾値と対象章を凍結)",
        "method": (
            "章番号で対応づけず、文の単位で二版を整列した。1845 年版の各章に対応する "
            "1839 年版の範囲は、整列で一致した文の最小・最大位置で決める。"
        ),
        "sources": {
            "1845": {"file": SRC_1845.name, "chapters": 21, "sentences": len(sent45)},
            "1839": {"file": SRC_1839.name, "chapters": 23, "sentences": len(sent39)},
        },
        "alignment": {
            "matching_blocks": len(blocks),
            "matched_sentences": matched_sents,
            "matched_pct_of_1845": round(matched_sents / len(sent45) * 100, 1),
        },
        "totals": {"words_1845": words45_total, "words_1839": words39_total},
        "chapters": rows,
        "ranking_desc": [
            {"chapter_1845": r["chapter_1845"], "ratio": r["ratio"], "rank": r["rank"]}
            for r in ranked
        ],
        "gates": gates,
        "verdict": "成立" if all(g["passes"] for g in gates.values()) else "不成立",
    }


def main() -> None:
    d = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    a = d["alignment"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  文 1845 {d['sources']['1845']['sentences']:,} / 1839 {d['sources']['1839']['sentences']:,}")
    print(f"  一致ブロック {a['matching_blocks']:,} / 一致文 {a['matched_sentences']:,}"
          f"({a['matched_pct_of_1845']}% of 1845)")
    print(f"  総語数 1845 {d['totals']['words_1845']:,} / 1839 {d['totals']['words_1839']:,}")
    for gid, g in d["gates"].items():
        print(f"  {gid} {'通過' if g['passes'] else '不通過'} — {g['claim']} → {g['measured']}")
    print(f"  判定: {d['verdict']}")


if __name__ == "__main__":
    main()
