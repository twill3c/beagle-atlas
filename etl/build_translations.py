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
    "etl.translations_c06_a",
    "etl.translations_c06_b",
    "etl.translations_c06_c",
    "etl.translations_c07_a",
    "etl.translations_c07_b",
    "etl.translations_c07_c",
    "etl.translations_c07_d",
    "etl.translations_c08_a",
    "etl.translations_c08_b",
    "etl.translations_c08_c",
    "etl.translations_c08_d",
    "etl.translations_c08_e",
    "etl.translations_c08_f",
    "etl.translations_c09_a",
    "etl.translations_c09_b",
    "etl.translations_c09_c",
    "etl.translations_c09_d",
    "etl.translations_c09_e",
    "etl.translations_c10_a",
    "etl.translations_c10_b",
    "etl.translations_c10_c",
    "etl.translations_c10_d",
]

# 日本語の中に紛れた半角ラテン文字を検出する(GEN-CHARS の型)。
# 学名・書誌参照・数値は正当なので、カタカナに挟まれた単独のラテン小文字だけを見る
LATIN_IN_KANA = re.compile(r"[ァ-ヶー][A-Za-z][ァ-ヶー]")

# 編集用の記法が訳文に漏れるのを止める。
# 訳文モジュールの docstring では強調に ** を使うが、**訳文そのものは素の本文**で
# なければならない —— 漏れると読み手の画面にアスタリスクがそのまま出る。
# 第 8 章で一度実際に漏らしたので、目視でなく検査で捕まえる形にした。
EDITORIAL_MARKUP = re.compile(r"\*\*|^#{1,6} |\[\[|\]\]", re.MULTILINE)

# 訳し漏らした英単語が日本語のなかに残るのを止める。
# 学名・書誌参照・原語の引用は正当なので**狙いを絞る** —— 日本語に直接隣接する
# 小文字のラテン語だけを見て、直前に大文字始まりの語があるもの(種小名・書誌の
# 一部)は除く。第 5・6・8 章で実際に 4 件(territory ×2・viceroy・favour)を
# 目視で見つけたので機械化した。
# 残すと決めた原語は KEPT に**登録する** —— 総当たりの許可リストにすると
# 形骸化するので、ここは小さく保つ(HC-160「例外を足し続けてゲートを壊す」)。
_JP = r"[ぁ-んァ-ヶー一-龥、。「」]"
BARE_ENGLISH = re.compile(rf"(?<![A-Za-z][ .]){_JP}[ 　]?([a-z]{{3,}})[ 　]?{_JP}")
KEPT_FOREIGN = {
    "huachos",     # 散らばったダチョウの卵(著者が原語のまま使う)
    "casarita",    # 小さな家建て(鳥の俗称)
    "mactra",      # 貝の属名の小文字表記
    "rincon",      # 二辺を水に守られた地形
    "nata", "niata",  # 短頭の牛の品種名
    "solen", "ampullariae", "hydrophilus",  # 単独で使われる種小名
    "petise",      # Avestruz Petise の小文字表記
    "inermis",     # Cynara の変種名
    "conejos",     # マゼランが用いたスペイン語(著者が原語のまま引く)
}


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

    # 編集用の記法が訳文に漏れていないか(docstring の強調が本文に落ちる型)
    marked = {k: EDITORIAL_MARKUP.findall(v) for k, v in items.items() if EDITORIAL_MARKUP.search(v)}
    if marked:
        raise ValueError(f"訳文に編集用の記法が混入: {marked}")

    # 訳し漏らした英単語が残っていないか(残す原語は KEPT_FOREIGN に登録する)
    left: dict[str, list[str]] = {}
    for k, v in items.items():
        ws = [w for w in BARE_ENGLISH.findall(v) if w not in KEPT_FOREIGN]
        if ws:
            left[k] = ws
    if left:
        raise ValueError(f"訳文に未訳の英単語が残存(残すなら KEPT_FOREIGN に登録): {left}")

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
