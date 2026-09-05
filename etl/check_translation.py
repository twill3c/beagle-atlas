"""訳の検査(SPEC F-07 / G-12)。

**訳の巧拙は測らない。** それを測ろうとすると、訳した当人が採点することになって循環する。
測るのは一つだけ ——「**原文の何が落ちたか**」である。

原文側の鍵になるのは、訳しても値が変わらないもの:

- **数** —— 距離・高度・温度・個数・脚注番号。訳文にそのまま現れるべき
- **段落の対応** —— 訳した段落は原文の段落と 1 対 1

これらは訳の良し悪しと独立に判定できる。逆に言えば、**この検査を通っても訳が良いとは言えない**。

**学名の保存は検査から外した(2026-09-05)。** 当初は「ラテン語の二名法は原綴のまま通す約束に
すれば、出現の一致を要求できる」と設計していた。ところが**資料に学名を見分ける信号が無い** ——
底本のイタリック記法(`_..._`)は 47 箇所しか使われておらず、その中身は `pichy` `ombu` `rancho`
といったスペイン語の借用語で、学名ではない。そこで「大文字始まりの語 + 小文字の語」という
規則で拾おうとしたところ、`This was` `Patagonia and` `English landscape` を学名と判定した。
**撃つべきでないものに撃つ検査は、無いほうがましである。** 学名は訳文中に原綴で残しているが、
それを機械で保証はしない。

    python -m etl.check_translation
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEXT = DATA / "text.json"
TRANS = DATA / "translations.json"

# 数: 整数・小数・桁区切り。序数の接尾辞は落とす
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(text: str) -> list[str]:
    return [n.replace(",", "") for n in NUM_RE.findall(text)]


def check() -> dict:
    text = json.loads(TEXT.read_text(encoding="utf-8"))
    trans = json.loads(TRANS.read_text(encoding="utf-8")) if TRANS.exists() else {"items": {}}
    items = trans.get("items", {})
    by_id = {it["id"]: it for c in text["chapters"] for it in c["items"]}

    problems: list[dict] = []
    checked = 0
    for pid, ja in items.items():
        src = by_id.get(pid)
        if src is None:
            problems.append({"id": pid, "kind": "unknown_id", "detail": "原文に無い段落 ID"})
            continue
        checked += 1
        want_n = sorted(numbers(src["text"]))
        got_n = sorted(numbers(ja))
        missing = [n for n in want_n if n not in got_n]
        if missing:
            problems.append({"id": pid, "kind": "number_lost", "detail": missing})
        if not ja.strip():
            problems.append({"id": pid, "kind": "empty", "detail": "訳が空"})

    total = text["totals"]["paragraphs"]
    return {
        "schema": "beagle-atlas/translation_check@1",
        "note": "訳の巧拙は測らない。測るのは『原文の何が落ちたか』だけである。",
        "totals": {
            "paragraphs_total": total,
            "translated": checked,
            "fill_rate": round(checked / total, 4),
            "problems": len(problems),
        },
        "problems": problems,
    }


def main() -> int:
    r = check()
    t = r["totals"]
    print(f"充填 {t['translated']} / {t['paragraphs_total']:,} 段落({t['fill_rate'] * 100:.1f}%)")
    print(f"検査の指摘 {t['problems']} 件")
    for p in r["problems"][:12]:
        print(f"  {p['id']} {p['kind']}: {p['detail']}")
    return 1 if r["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
