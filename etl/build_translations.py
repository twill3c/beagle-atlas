"""訳をまとめて data/translations.json にする(SPEC F-07)。

訳は章ごとの Python モジュールに置き、ここで束ねる。**段落 ID に紐づける**ので、
`etl/build_text.py` が振る ID を後から動かしてはならない。

底本は 1845 年第 2 版(パブリックドメイン)。訳は自前。**巧拙は主張しない** ——
主張するのは充填率と、原文の何が落ちていないかだけである。

    python -m etl.build_translations
"""
from __future__ import annotations

import importlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "translations.json"
TEXT = ROOT / "data" / "text.json"

MODULES = [
    "etl.translations_c01_a",
    "etl.translations_c01_b",
    "etl.translations_c01_c",
    "etl.translations_c02_a",
    "etl.translations_c02_b",
    "etl.translations_c02_c",
    "etl.translations_c03_a",
    "etl.translations_c03_b",
    "etl.translations_c03_c",
    "etl.translations_c03_d",
    "etl.translations_c04_a",
    "etl.translations_c04_b",
    "etl.translations_c04_c",
    "etl.translations_c05_a",
    "etl.translations_c05_b",
    "etl.translations_c05_c",
    "etl.translations_c05_d",
    "etl.translations_c05_e",
]

# 日本語の中に紛れた半角ラテン文字を検出する(GEN-CHARS の型)。
# 学名・書誌参照・数値は正当なので、カタカナに挟まれた単独のラテン小文字だけを見る
LATIN_IN_KANA = re.compile(r"[ァ-ヶー][A-Za-z][ァ-ヶー]")


def load() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in MODULES:
        mod = importlib.import_module(name)
        for k, v in mod.TRANSLATIONS.items():
            if k in out:
                raise ValueError(f"段落 ID の重複: {k}")
            out[k] = unicodedata.normalize("NFC", v)
    return out


def main() -> None:
    items = load()
    text = json.loads(TEXT.read_text(encoding="utf-8"))
    known = {it["id"] for c in text["chapters"] for it in c["items"]}
    unknown = sorted(set(items) - known)
    if unknown:
        raise ValueError(f"原文に無い段落 ID: {unknown}")

    # 字種の混入を止める(text_hygiene はカタカナ内のラテン文字を見ない)
    bad = {k: LATIN_IN_KANA.findall(v) for k, v in items.items() if LATIN_IN_KANA.search(v)}
    if bad:
        raise ValueError(f"カタカナに半角ラテン文字が混入: {bad}")

    by_chapter: dict[str, int] = {}
    for k in items:
        by_chapter[k[:3]] = by_chapter.get(k[:3], 0) + 1

    data = {
        "schema": "beagle-atlas/translations@1",
        "policy": (
            "底本は 1845 年第 2 版(パブリックドメイン)。訳は自前で、巧拙は主張しない。"
            "既存の邦訳は参照も照合もしていない。主張するのは充填率と、"
            "原文の何が落ちていないかだけである。"
        ),
        "totals": {
            "translated": len(items),
            "paragraphs_total": text["totals"]["paragraphs"],
            "fill_rate": round(len(items) / text["totals"]["paragraphs"], 4),
            "by_chapter": by_chapter,
        },
        "items": dict(sorted(items.items())),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    t = data["totals"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  充填 {t['translated']} / {t['paragraphs_total']:,} 段落({t['fill_rate'] * 100:.1f}%)")
    print(f"  章別: {t['by_chapter']}")


if __name__ == "__main__":
    main()
