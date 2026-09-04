"""版差分の検査(G-20a / G-20b / G-20c)。

**主張が通ることを検査しない。** 事前登録した目玉は G-20c で落ちており(SPEC §6.0)、
テストが「通ること」を要求したら、次に測り直したとき正しい実装の方が落ちる。
ここで守るのは (1) 計器の健全性、(2) 記録された判定が実測値と一致すること、の二つである。
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIFF = ROOT / "data" / "edition_diff.json"

pytestmark = pytest.mark.skipif(
    not DIFF.exists(), reason="data/edition_diff.json が無い(python -m etl.edition_diff で作る)"
)

GALAPAGOS_CHAPTER = 17  # SPEC §6.0 で測定前に固定した対象


@pytest.fixture(scope="session")
def diff():
    return json.loads(DIFF.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_t060_partition_conserves_1839_words(diff):
    """T-060: 1839 年版の語がちょうど一度ずつ数えられている(計器の健全性)。

    最初の実装は「一致した文の最小・最大」で範囲を取っており、
    アンカーの疎な章で比が跳ね上がっていた。**保存則がその誤りを捕まえる。**
    """
    total = sum(r["words_1839_aligned"] for r in diff["chapters"])
    assert total == diff["totals"]["words_1839"]


@pytest.mark.unit
def test_t061_chapter_bounds_are_monotonic(diff):
    """T-061: 1845 年版の章に割り当てた 1839 年側の範囲が単調で、隙間も重なりも無い。"""
    spans = [r["span_1839"] for r in diff["chapters"]]
    assert spans[0][0] == 0
    for a, b in zip(spans, spans[1:]):
        assert a[1] == b[0], f"境目が繋がっていない: {a} → {b}"


@pytest.mark.unit
def test_t062_g20a_total_shrank(diff):
    """T-062(G-20a): 第 2 版は全体で縮んだ。Freeman の記述との検算であり予測ではない。"""
    g = diff["gates"]["G-20a"]
    assert g["passes"] is (diff["totals"]["words_1845"] < diff["totals"]["words_1839"])
    assert g["passes"], "全体が縮んでいない。Freeman の記述と食い違うので要調査"


@pytest.mark.unit
def test_t063_g20b_galapagos_ratio_matches_record(diff):
    """T-063(G-20b): 記録された判定が、章別表の実測値と一致する。"""
    row = next(r for r in diff["chapters"] if r["chapter_1845"] == GALAPAGOS_CHAPTER)
    g = diff["gates"]["G-20b"]
    assert g["measured"]["chapter"] == GALAPAGOS_CHAPTER
    assert g["measured"]["ratio"] == row["ratio"]
    assert g["passes"] is (row["ratio"] > 1.0)


@pytest.mark.unit
def test_t064_g20c_rank_matches_record(diff):
    """T-064(G-20c): 記録された順位が、比の降順から導かれた値と一致する。

    **この検査は「上位 3 位以内であること」を要求しない。** 実測は 4 位で落ちており
    (SPEC §6.0)、閾値は緩めない。守るのは記録と実測の一致だけである。
    """
    ranked = sorted(
        (r for r in diff["chapters"] if r["ratio"] is not None),
        key=lambda r: r["ratio"],
        reverse=True,
    )
    rank = next(
        i for i, r in enumerate(ranked, 1) if r["chapter_1845"] == GALAPAGOS_CHAPTER
    )
    g = diff["gates"]["G-20c"]
    assert g["measured"]["rank"] == rank
    assert g["measured"]["of"] == len(ranked)
    assert g["passes"] is (rank <= 3)


@pytest.mark.unit
def test_t065_verdict_matches_gates(diff):
    """T-065: 総合判定が個々のゲートの結果と食い違わない。"""
    all_pass = all(g["passes"] for g in diff["gates"].values())
    assert diff["verdict"] == ("成立" if all_pass else "不成立")
    # 実測 2026-09-05: G-20c が落ちているので不成立。ここが「成立」に変わったら、
    # 閾値が緩められたか計器が変わったかのどちらかで、どちらも要調査。
    assert diff["verdict"] == "不成立"
