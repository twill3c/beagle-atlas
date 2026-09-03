"""底本の取得と二経路照合(G-01 / G-02 / G-14 / G-14b)。

期待値の出所は TEST_SPEC.md「オラクルの出所」および各ケースのコメントに記す。
S-A(Darwin Online F14)と S-B(Project Gutenberg #944)は同一版の独立した二翻刻であり、
どちらかを正解と仮定して他方を採点するのではなく、食い違いを検出して台帳に出す。
"""
import re
from pathlib import Path

import pytest

from etl import sources

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"

# 台帳(TEST_SPEC.md「既知の翻刻異常」)。2026-09-04 の二経路照合で検出した。
KNOWN_ANOMALY_CHAPTERS = {20}


@pytest.fixture(scope="session")
def do_paras():
    paras, _dropped = sources.load_darwin_online(RAW / "f14.converted.html")
    return paras


@pytest.fixture(scope="session")
def pg_paras():
    return sources.load_gutenberg(RAW / "pg944.body.txt")


# ---------- G-01 版の確定 ----------


@pytest.mark.unit
def test_t001_edition_is_1845_second_edition(do_paras, pg_paras):
    """T-001: 版は書誌ではなく本文で確定する。序文末の日付が根拠(SPEC §3)。

    出所: 本文実測 2026-09-04。PG の書誌ページは 'published in 1839' と表示するため、
    メタデータを信じてはならない。

    **両経路に要求するのは年まで**である。S-A は署名の日の数字と地名行を欠く
    (`June , 1845.` = 台帳 E-02)。完全な日付は S-B から採る。
    SPEC の保証粒度を超える期待値を書かない(HC-016)。
    """
    # 署名は巻頭の**短い**段落である。長い段落を許すと本文中の脚注 "(June, 1845)" が
    # 偶然拾われ、テストが誤った理由で緑になる(実測: S-A 段落 109 がその形)。
    year = re.compile(r"\bJune\b[^.]{0,40}\b1845\b", re.I)
    for label, paras in (("S-A", do_paras), ("S-B", pg_paras)):
        head = paras[: len(paras) // 10]  # 序文は巻頭にある
        signature = [p for p in head if len(p) <= 60 and year.search(p)]
        assert signature, f"{label}: 序文の署名(1845 年付)が無い"

    full = re.compile(r"June\s+9,?\s+1845", re.I)
    assert any(full.search(p) for p in pg_paras), "S-B: 完全な日付が見つからない"


@pytest.mark.unit
def test_t002_chapter_count_agrees(do_paras, pg_paras):
    """T-002: 本文側の章見出しが両経路とも 21 件(実測 2026-09-04・L0-1)。"""
    do_spans, _ = sources.chapter_spans(do_paras)
    pg_spans, _ = sources.chapter_spans(pg_paras)
    assert len(do_spans) == len(pg_spans) == sources.N_CHAPTERS
    assert set(do_spans) == set(pg_spans) == set(range(1, sources.N_CHAPTERS + 1))


# ---------- G-02 配布元ヘッダ・フッタの除去 ----------


@pytest.mark.unit
def test_t003_no_distributor_boilerplate_in_body():
    """T-003: 除去後の本文に配布元の商標残存参照が無い(SPEC §3・実測 2026-09-04)。"""
    body = (RAW / "pg944.body.txt").read_text(encoding="utf-8", errors="replace")
    assert sources.count_distributor_mentions(body) == 0


@pytest.mark.unit
def test_t004_positive_control_raw_file_has_boilerplate():
    """T-004: 陽性対照。除去前の生ファイルには残存参照がある。

    これが撃たなければ、T-003 の 0 件は「検査が働いていない」ことと区別できない(G-10)。
    """
    raw = (RAW / "pg944.raw.txt").read_text(encoding="utf-8", errors="replace")
    assert sources.count_distributor_mentions(raw) > 0


# ---------- G-14 二経路照合 ----------


@pytest.mark.validation
def test_t005_multiset_agreement_all_chapters(do_paras, pg_paras):
    """T-005: 全 21 章で語彙保存(多重集合)≥ 0.94(SPEC §10 G-14)。

    閾値の出所: L0-6 の実測(中央値 0.9911 / 最小 0.9494・2026-09-04)に余裕を取った値。
    **順序込みの一致率を閾値にしてはならない** —— 脚注の位置が両翻刻で異なるため、
    欠落が無くても 0.95 前後に落ちる(L0-7)。
    """
    scores = sources.chapter_agreements(do_paras, pg_paras)
    bad = {n: s.multiset for n, s in scores.items() if s.multiset < 0.94}
    assert not bad, f"語彙保存が閾値を下回る章: {bad}"


@pytest.mark.validation
def test_t006_sequence_agreement_is_recorded_not_gated(do_paras, pg_paras):
    """T-006: 順序込み一致率は記録するのみで閾値にしない(L0-7)。

    全 21 章について値が得られること自体を確かめる(欠測が無いこと)。
    """
    scores = sources.chapter_agreements(do_paras, pg_paras)
    assert len(scores) == sources.N_CHAPTERS
    assert all(0.0 <= s.sequence <= 1.0 for s in scores.values())


# ---------- G-14b 既知の翻刻異常 ----------


@pytest.mark.unit
def test_t007_positive_control_known_anomaly_is_reported(do_paras):
    """T-007: 陽性対照。E-01(S-A 第 20 章の見出しが CHAPTER XXX)を検査が報告する。

    出所: 台帳 TEST_SPEC.md「既知の翻刻異常」(実測 2026-09-04)。
    """
    _spans, anomalies = sources.chapter_spans(do_paras)
    reported = {a.ordinal for a in anomalies}
    assert KNOWN_ANOMALY_CHAPTERS <= reported, f"E-01 が報告されない: {anomalies}"
    got = next(a for a in anomalies if a.ordinal == 20)
    assert got.roman == "XXX"


@pytest.mark.unit
def test_t008_no_anomaly_outside_the_ledger(do_paras, pg_paras):
    """T-008: 台帳に無い章で異常を報告しない(撃つべきでないものに撃たない・G-10)。"""
    _s, do_anom = sources.chapter_spans(do_paras)
    _s2, pg_anom = sources.chapter_spans(pg_paras)
    assert {a.ordinal for a in do_anom} == KNOWN_ANOMALY_CHAPTERS
    assert pg_anom == [], f"S-B に未知の異常: {pg_anom}"


# ---------- 組版残滓・総語数・索引 ----------


@pytest.mark.unit
def test_t009_typographic_residue_removed(do_paras):
    """T-009: S-A の頁番号・折丁記号が除去される(実測 2026-09-04・541 段落)。

    件数は定数で書かず「残っていない」という不変量で書く(HC-016)。
    """
    residue = [p for p in do_paras if sources.JUNK_RE.match(p)]
    assert residue == []


@pytest.mark.unit
def test_t010_total_wordcount_within_freeman_band(do_paras, pg_paras):
    """T-010: 総語数が Freeman の記す約 213,000 語の帯に収まる。

    出所: Darwin Online, Freeman "Journal of Researches" 解題(取得 2026-09-03)。
    SPEC の保証粒度は「帯」なので、点推定を要求しない(HC-016)。
    """
    for label, paras in (("S-A", do_paras), ("S-B", pg_paras)):
        n = len(sources.norm_words(" ".join(paras)))
        assert 190_000 <= n <= 240_000, f"{label}: 総語数 {n:,} が帯の外"


@pytest.mark.unit
def test_t011_index_present_only_in_darwin_online(do_paras, pg_paras):
    """T-011: 1845 年版の索引は S-A のみが収録する(実測 2026-09-04・L0-10)。"""
    assert sources.find_index_start(do_paras) is not None
    assert sources.find_index_start(pg_paras) is None
