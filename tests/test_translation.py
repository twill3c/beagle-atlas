"""訳の検査(SPEC F-07 / G-12)。

**訳の巧拙は検査しない。** 訳した当人が採点すれば循環する。
守るのは「原文の何が落ちたか」と、充填率が正しく数えられていることだけ。
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "data" / "text.json"
TRANS = ROOT / "data" / "translations.json"

pytestmark = pytest.mark.skipif(
    not (TEXT.exists() and TRANS.exists()),
    reason="text.json / translations.json が無い(etl で作る)",
)


@pytest.fixture(scope="session")
def text():
    return json.loads(TEXT.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def trans():
    return json.loads(TRANS.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_t080_g12_numbers_are_preserved(text, trans):
    """T-080(G-12): 原文の数が訳文から落ちていない。

    距離・高度・年・脚注番号は訳しても値が変わらないので、そのまま現れるべき。
    実測 2026-09-05: 第 1 章 39 段落で指摘 0 件。
    """
    from etl.check_translation import check

    r = check()
    lost = [p for p in r["problems"] if p["kind"] == "number_lost"]
    assert lost == [], f"数が落ちた段落: {lost[:5]}"


@pytest.mark.unit
def test_t081_ids_resolve_and_no_empty(text, trans):
    """T-081(F-07): 訳の段落 ID が原文に存在し、空の訳が無い。"""
    known = {it["id"] for c in text["chapters"] for it in c["items"]}
    unknown = sorted(set(trans["items"]) - known)
    assert unknown == [], f"原文に無い段落 ID: {unknown}"
    empty = [k for k, v in trans["items"].items() if not v.strip()]
    assert empty == [], f"空の訳: {empty}"


@pytest.mark.unit
def test_t082_fill_rate_matches_the_count(text, trans):
    """T-082(F-07): 充填率が実際の件数から導かれている。

    **分子と分母の両方を出す**のが方針なので、表示の元になる数が
    実データと食い違っていないことを確かめる。
    """
    t = trans["totals"]
    assert t["translated"] == len(trans["items"])
    assert t["paragraphs_total"] == text["totals"]["paragraphs"]
    assert t["fill_rate"] == pytest.approx(
        t["translated"] / t["paragraphs_total"], abs=5e-5
    )


@pytest.mark.unit
def test_t083_positive_control_lost_number_is_caught():
    """T-083(G-12): 陽性対照。数を落とした訳を検査が撃つ。

    これが撃たなければ、T-080 の 0 件は「落ちていない」ことと
    「検査が働いていない」ことを区別できない(G-10)。
    """
    from etl.check_translation import numbers

    src = "We sailed on the 27th of December, 1831, in a ten-gun brig."
    ja_ok = "われわれは 1831 年 12 月 27 日、十門の帆船で出航した。"
    ja_bad = "われわれは十二月に、十門の帆船で出航した。"
    want = sorted(numbers(src))
    assert [n for n in want if n not in sorted(numbers(ja_ok))] == []
    assert [n for n in want if n not in sorted(numbers(ja_bad))] != []
