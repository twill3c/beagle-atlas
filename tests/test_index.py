"""1845 年版索引のパース(O-1b / G-03 の前提)。

期待値は 2026-09-04 に実データ全域を走査してから書いた(HC-069)。
索引そのものの癖(下位項目が非整列・J が I より前・終端が印刷標識)は
TEST_SPEC.md「索引のパース」に記す。
"""
import re
from pathlib import Path

import pytest

from etl import index as idx
from etl import sources

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
F14 = RAW / "f14.converted.html"

# 1845 年の組版に見られる I/J 合併配列。索引では J の項目群が I より前に来る。
# 実測 2026-09-04: 頭文字の逆転はこの 1 箇所のみ。
KNOWN_LETTER_INVERSIONS = {("J", "I")}

# 頁範囲の二表記(実測 2026-09-04: `N to M` 12 行 / `N—M` 2 行)
_RANGE_RE = re.compile(r"(\d{1,3})(?:\s+to\s+|\s*[—–]\s*)(\d{1,3})")
# 座標表記の数は頁参照ではない(実測 2026-09-04: `——— in lat. 46° 40′, 246` の 1 行のみ)
_COORD_RE = re.compile(r"\d{1,3}\s*[°′″]")


def _page_refs_in(text: str) -> set[int]:
    """索引の 1 行から、パーサを使わずに頁参照を拾う(独立集計)。"""
    text = _COORD_RE.sub(" ", text)
    pages: set[int] = set()
    for a, b in _RANGE_RE.findall(text):
        pages.update(range(int(a), int(b) + 1))
    text = _RANGE_RE.sub(" ", text)
    pages.update(int(n) for n in re.findall(r"\b(\d{1,3})\b", text))
    return pages


@pytest.fixture(scope="session")
def paras():
    p, _dropped = sources.load_darwin_online(F14)
    return p


@pytest.fixture(scope="session")
def entries(paras):
    return idx.parse_index(paras)


@pytest.fixture(scope="session")
def page_bounds():
    """本の頁範囲は [page N] マーカーから導出する(定数で書かない・T-023)。"""
    return sources.book_page_bounds(F14)


# ---------- 終端 ----------


@pytest.mark.unit
def test_t020_body_ends_at_printed_marker(paras):
    """T-020: 索引本体の終端は印刷された `THE END.`(実測 2026-09-04)。

    辞書順や頁範囲から終端を推定する必要はない —— 本が終端を印刷している。
    """
    start, end = idx.find_index_body(paras)
    assert start < end
    body = paras[start:end]
    assert body, "索引本体が空"
    assert not any(idx.is_end_mark(t) for t in body), "本体に終端標識が残っている"
    assert idx.is_end_mark(paras[end]), "終端の次が終端標識でない"


# ---------- 取りこぼしの不在 ----------


@pytest.mark.unit
def test_t021_every_line_is_classified(paras, entries):
    """T-021: 全行がいずれかの型に分類される。未分類は黙って捨てず例外で止める。"""
    start, end = idx.find_index_body(paras)
    assert len(entries) == end - start, "行数と項目数が一致しない(取りこぼしがある)"
    assert all(e.kind in idx.KINDS for e in entries)


@pytest.mark.unit
def test_t021b_unclassifiable_line_raises(paras):
    """T-021 の陽性対照: 分類できない行を混ぜたら例外で止まる。"""
    start, end = idx.find_index_body(paras)
    broken = list(paras)
    broken.insert(start, "")  # どの型にも当たらない行
    with pytest.raises(idx.UnclassifiedLine):
        idx.parse_index(broken)


# ---------- 継承 ----------


@pytest.mark.unit
def test_t022_continuations_inherit_a_parent(entries):
    """T-022: 継続行(———)は必ず直前の見出し語を継承する(実測 2026-09-04・382 行)。"""
    assert entries[0].kind != "continuation", "索引の先頭が継続行"
    conts = [e for e in entries if e.kind == "continuation"]
    assert conts, "継続行が 1 件も無い(検出器が働いていない疑い)"
    assert all(e.headword for e in conts), "親の見出し語を持たない継続行がある"


# ---------- 頁参照 ----------


@pytest.mark.unit
def test_t023_all_page_refs_within_book(entries, page_bounds):
    """T-023: 全ての頁参照が本の頁範囲に収まる。範囲は頁マーカーから導出する。"""
    lo, hi = page_bounds
    assert lo >= 1 and hi > lo
    bad = idx.out_of_range_refs(entries, lo, hi)
    assert bad == [], f"頁範囲 {lo}–{hi} を外れる参照: {bad[:5]}"


@pytest.mark.unit
def test_t024_positive_control_out_of_range_is_caught():
    """T-024: 陽性対照。範囲外の頁を持つ項目を検査が撃つ。

    これが撃たなければ T-023 の 0 件は「検査が働いていない」ことと区別できない(G-10)。
    """
    planted = idx.IndexEntry(
        line=0, raw="Planted, 9999", kind="headword", headword="Planted",
        subentry=None, pages=(9999,), ranges=(), see=None,
    )
    assert idx.out_of_range_refs([planted], 1, 536)


@pytest.mark.unit
def test_t025_page_ranges_parsed(entries):
    """T-025: `N to M` 形式が範囲として解釈され、取りこぼしが無い。

    母集団は**索引本体**である(実測 2026-09-04: 12 件)。
    `THE END.` 以降の出版社広告にも `1832 to 1836` の形があるので、
    そこまで含めて数えると 17 件になる —— 別の母集団の数である(HC-152)。
    件数は定数で書かず「取りこぼしが無い」という不変量で書く。
    """
    ranged = [e for e in entries if e.ranges]
    assert ranged, "範囲を持つ項目が 1 件も無い"
    for e in ranged:
        for a, b in e.ranges:
            assert a < b, f"範囲の向きが逆: {e.raw!r}"

    looks_ranged = re.compile(r"\d+\s+to\s+\d+")
    missed = [e.raw for e in entries if looks_ranged.search(e.raw) and not e.ranges]
    assert missed == [], f"範囲を取りこぼした行: {missed}"


@pytest.mark.unit
def test_t026_cross_reference_has_no_pages(entries):
    """T-026: 相互参照(`see`)は頁を持たない項目になる(実測 2026-09-04・1 件)。"""
    xrefs = [e for e in entries if e.see]
    assert xrefs, "相互参照が 1 件も無い"
    for e in xrefs:
        assert e.pages == () and e.ranges == ()
        assert e.see.strip()


# ---------- 並び ----------


@pytest.mark.unit
def test_t027_letters_monotonic_except_known_ij(entries):
    """T-027: 頭文字は I/J の既知の入れ替えを除いて単調(実測 2026-09-04)。

    **素朴な辞書順検査は落ちる** —— 下位項目は整列されていないので、
    検査は頭文字の水準でのみ成り立つ。
    """
    found = idx.first_letter_inversions(entries)
    assert set(found) == KNOWN_LETTER_INVERSIONS, f"既知以外の逆転: {set(found) - KNOWN_LETTER_INVERSIONS}"


@pytest.mark.unit
def test_t028_positive_control_inversion_is_caught():
    """T-028: 陽性対照。壊した並びで逆転が報告される。"""

    def mk(word):
        return idx.IndexEntry(
            line=0, raw=word, kind="headword", headword=word,
            subentry=None, pages=(1,), ranges=(), see=None,
        )

    shuffled = [mk("Apple"), mk("Zebra"), mk("Banana")]
    assert idx.first_letter_inversions(shuffled), "壊した並びに撃たない"


# ---------- gold としての使い勝手 ----------


@pytest.mark.unit
def test_t030_no_page_reference_is_dropped(entries):
    """T-030: 行に現れる頁参照を一つも落とさない(独立集計との一致)。

    この不変量が無かったために、**セミコロンで複合した項目の前半の頁**が
    黙って落ちていた(`Galapagos Archipelago, 372; natural history of, 377` の 372)。
    行末の頁ブロックだけを見る実装では、区切りごとに頁を持つ行を取りこぼす。
    検出は 2026-09-04 の独立再計算による —— テストはすり抜けていた(VERIF-GAP)。
    """
    dropped = [(e.raw, sorted(m)) for e in entries if (m := _page_refs_in(e.raw) - set(e.all_pages))]
    assert dropped == [], f"頁参照を落とした行: {dropped[:5]}"


@pytest.mark.unit
def test_t030b_positive_control_dropping_is_caught():
    """T-030 の陽性対照: 頁を落とした項目を検査が撃つ。"""
    bad = idx.IndexEntry(
        line=0, raw="Compound, 372; more of it, 377", kind="headword",
        headword="Compound", subentry="more of it", pages=(377,), ranges=(), see=None,
    )
    assert _page_refs_in(bad.raw) - set(bad.all_pages), "落とした頁を検出できていない"

    # 対照の対照: 座標表記は頁参照として数えない
    coord = idx.IndexEntry(
        line=0, raw="——— in lat. 46° 40′, 246", kind="continuation",
        headword="Soundings", subentry="in lat. 46° 40′", pages=(246,), ranges=(), see=None,
    )
    assert _page_refs_in(coord.raw) - set(coord.all_pages) == set()


@pytest.mark.unit
def test_t029_nearly_all_entries_carry_pages(entries):
    """T-029: 頁を持つ項目が本体の 99% 以上(実測 2026-09-04: 数字なしは 1 行のみ)。"""
    with_pages = [e for e in entries if e.pages or e.ranges]
    assert len(with_pages) / len(entries) >= 0.99
