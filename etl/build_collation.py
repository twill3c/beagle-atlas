"""底本の二経路照合を成果物として書き出す(SPEC §10 G-14)。

出力は `data/collation.json`。画面はこの値を読むだけにして、
**数値を画面側に決め打ちしない**(G-11)。

    python -m etl.build_collation
"""
from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

from etl import sources

ROOT = Path(__file__).resolve().parents[1]
SRC_A = ROOT / "raw" / "f14.converted.html"
SRC_B = ROOT / "raw" / "pg944.body.txt"
OUT = ROOT / "data" / "collation.json"

# 台帳(TEST_SPEC.md「既知の翻刻異常」)
LEDGER = [
    {
        "id": "E-01",
        "side": "S-A",
        "where": "本文 第 20 章 見出し",
        "observed": "CHAPTER XXX.",
        "expected": "CHAPTER XX.",
        "handling": "黙って書き換えない。序数で対応づけ、異常として報告する",
    },
    {
        "id": "E-02",
        "side": "S-A",
        "where": "序文の署名",
        "observed": "June , 1845.",
        "expected": "DOWN, BROMLEY, KENT, June 9, 1845",
        "handling": "版の確定は年で行い、完全な日付は S-B から採る。閾値化しない",
    },
    {
        "id": "E-03",
        "side": "S-B",
        "where": "本文 第 6 章 冒頭の日付(段落 c06p001)",
        "observed": "SEPTEMBER 18th.",
        "expected": "SEPTEMBER 8th.",
        "handling": (
            "黙って書き換えない。**日付の内部整合が非循環に裁定する** —— "
            "章の日付は 9(c06p004)・10・11・12と13・14・15・16・17・18(c06p024)・"
            "19・20 と一日ずつ欠けなく進む。章頭を 8 と読めば 8〜20 の連続になるが、"
            "18 と読むと (a) 順序が最初で壊れ、(b) 同じ 18 日が章の最初と最後に"
            "二度現れ、(c) あいだの十日が行き場を失う。S-A は 8th と読む。"
            "**読み本文は S-B なので、読み手に見えるのはこの誤り**である。"
            "台帳に載せたうえで本文はそのまま出し、訳もそのまま訳す"
        ),
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    do_paras, do_dropped = sources.load_darwin_online(SRC_A)
    pg_paras = sources.load_gutenberg(SRC_B)
    scores = sources.chapter_agreements(do_paras, pg_paras)
    _spans, anomalies = sources.chapter_spans(do_paras)

    seq = sorted(s.sequence for s in scores.values())
    mul = sorted(s.multiset for s in scores.values())

    body_a = sum(s.words_a for s in scores.values())
    body_b = sum(s.words_b for s in scores.values())
    all_a = len(sources.norm_words(" ".join(do_paras)))
    all_b = len(sources.norm_words(" ".join(pg_paras)))

    return {
        "schema": "beagle-atlas/collation@1",
        "work": {
            "title": "Journal of Researches into the Natural History and Geology of the "
            "Countries Visited during the Voyage of H.M.S. Beagle round the World",
            "author": "Charles Darwin",
            "edition": "2nd ed.",
            "publisher": "London: John Murray",
            "year": 1845,
            "freeman": "F14",
            "copyright_status": "public domain",
        },
        "sources": {
            "A": {"role": "正本", "name": "Darwin Online (F14)", "sha256": sha256(SRC_A)},
            "B": {
                "role": "照合",
                "name": "Project Gutenberg #944(配布元のヘッダ・フッタを除去)",
                "sha256": sha256(SRC_B),
            },
        },
        "gate": {
            "id": "G-14",
            "measure": "multiset",
            "threshold": 0.94,
            "note": "閾値は語彙保存(順序無視)に置く。順序込みの一致率は脚注の配置差で"
            "下がるため、記録するのみで閾値にしない",
        },
        "totals": {
            "chapters": sources.N_CHAPTERS,
            "paragraphs_a": len(do_paras),
            "paragraphs_b": len(pg_paras),
            "typographic_residue_removed_a": do_dropped,
            "words_all_a": all_a,
            "words_all_b": all_b,
            "words_body_a": body_a,
            "words_body_b": body_b,
            "words_outside_chapters_a": all_a - body_a,
            "words_outside_chapters_b": all_b - body_b,
            "sequence_median": round(statistics.median(seq), 4),
            "sequence_min": round(min(seq), 4),
            "multiset_median": round(statistics.median(mul), 4),
            "multiset_min": round(min(mul), 4),
        },
        "chapters": [
            {
                "chapter": n,
                "words_a": s.words_a,
                "words_b": s.words_b,
                "sequence": round(s.sequence, 4),
                "multiset": round(s.multiset, 4),
                "passes_gate": s.multiset >= 0.94,
            }
            for n, s in sorted(scores.items())
        ],
        "anomalies_detected": [
            {"ordinal": a.ordinal, "roman": a.roman, "paragraph": a.paragraph_index}
            for a in anomalies
        ],
        "ledger": LEDGER,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    t = data["totals"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  章 {t['chapters']} / 語彙保存 中央値 {t['multiset_median']} 最小 {t['multiset_min']}")
    print(f"  順序込み 中央値 {t['sequence_median']} 最小 {t['sequence_min']}")
    print(f"  ゲート通過 {sum(1 for c in data['chapters'] if c['passes_gate'])}/{t['chapters']}")


if __name__ == "__main__":
    main()
