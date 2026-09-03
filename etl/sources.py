"""底本の読み込みと二経路照合(SPEC §3・§10 G-01 / G-02 / G-14)。

S-A = Darwin Online の翻刻(正本)、S-B = Project Gutenberg #944(照合)。
どちらも Darwin, *Journal of Researches*, 2nd ed. (London: John Murray, 1845) の翻刻で、
原文はパブリックドメイン。取得日・sha256・加工手順は raw/MANIFEST.json に固定してある。

方針:
- 段落の 1:1 対応は取れない(S-A の <p> は頁で分断される)。照合は **語列** で行う
- 章見出しは **序数** で対応づける。ローマ数字が序数と食い違ったら
  黙って直さず `ChapterAnomaly` として報告する(AGENTS.md「仮定が崩れたら落ちる検算」)
- 一致は **語彙保存(多重集合)** を主とする。順序込みの一致率は脚注の配置差で
  下がるため参考値に留める(SPEC L0-7)
"""
from __future__ import annotations

import html
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

N_CHAPTERS = 21

ROMAN_TO_INT = {
    r: i
    for i, r in enumerate(
        "I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII XVIII XIX XX XXI".split(), 1
    )
}

HEAD_RE = re.compile(r"^CHAPTER\s+([IVXL]+)\.?$", re.I)

# S-A の組版残滓: 単独の頁番号 / 折丁記号(2 F・2 G 2 等)/ ローマ数字頁 / ( 507 ) 形式
JUNK_RE = re.compile(r"^(?:\d{1,4}|[0-9]\s?[A-Z](?:\s?\d)?|[ivxlc]{1,7}|\(\s*\d{1,4}\s*\))$")

# 配布元(Project Gutenberg)が付した前書き・後書き・商標表示の検出語
DISTRIBUTOR_MARK = re.compile(r"gutenberg", re.I)

INDEX_HEAD_RE = re.compile(r"^INDEX\.?$")


@dataclass(frozen=True)
class ChapterAnomaly:
    """章見出しのローマ数字が序数と食い違った箇所。黙って直さず報告する。"""

    ordinal: int
    roman: str
    paragraph_index: int


@dataclass(frozen=True)
class Agreement:
    """一章分の二経路一致。"""

    chapter: int
    words_a: int
    words_b: int
    sequence: float  # 順序込み。参考値(閾値にしない — SPEC L0-7)
    multiset: float  # 語彙保存。G-14 の判定に使う


def norm_words(text: str) -> list[str]:
    """比較用の正規化: NFKC → 引用符・ダッシュ統一 → 小文字 → 記号除去 → 語列."""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("—", " ").replace("–", " ").replace("--", " ")
    t = t.lower()
    t = re.sub(r"[^a-z0-9'\s]", " ", t)
    return t.split()


def count_distributor_mentions(text: str) -> int:
    """配布元の商標残存参照の件数(G-02)。"""
    return len(DISTRIBUTOR_MARK.findall(text))


def load_darwin_online(path: str | Path) -> tuple[list[str], int]:
    """S-A の HTML → 段落列。頁マーカーと組版残滓を落とし、落とした数を返す。"""
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    dropped = 0
    for block in re.findall(r"<p\b[^>]*>(.*?)</p>", src, flags=re.S | re.I):
        text = re.sub(r"<[^>]+>", " ", block)
        text = html.unescape(text)
        text = re.sub(r"\[page[^\]]*\]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if JUNK_RE.match(text):
            dropped += 1
            continue
        out.append(text)
    return out, dropped


def load_gutenberg(path: str | Path) -> list[str]:
    """S-B のプレーンテキスト(配布元ヘッダ・フッタ除去済み)→ 論理段落列。"""
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    src = src.replace("_", "")  # S-B はイタリックを _..._ で表す(翻刻注記)
    out = []
    for block in re.split(r"\n\s*\n", src):
        block = re.sub(r"\s+", " ", block).strip()
        if block:
            out.append(block)
    return out


def find_index_start(paras: list[str]) -> int | None:
    """1845 年版の索引の開始段落。無ければ None(S-B は索引を収録しない)。"""
    hits = [i for i, p in enumerate(paras) if INDEX_HEAD_RE.match(p.strip())]
    return hits[-1] if hits else None


def chapter_spans(paras: list[str]) -> tuple[dict[int, tuple[int, int]], list[ChapterAnomaly]]:
    """本文側の章見出し 21 件を採り、[start, end) の範囲と異常の一覧を返す。

    目次にも同じ見出しが並ぶため、**末尾 21 件**を本文側として採る。
    採った並びの k 番目を第 k 章とし、ローマ数字が k と食い違えば異常として報告する
    (S-A 第 20 章の `CHAPTER XXX` = E-01 がこれで出る)。
    最終章の終端は、索引があればその手前で切る(索引・出版社広告を本文に含めない)。
    """
    hits = [
        (i, m.group(1).upper()) for i, p in enumerate(paras) if (m := HEAD_RE.match(p.strip()))
    ]
    if len(hits) < N_CHAPTERS:
        raise ValueError(f"章見出しが {len(hits)} 件しか無い(必要 {N_CHAPTERS})")
    body = hits[-N_CHAPTERS:]

    anomalies = [
        ChapterAnomaly(ordinal=k, roman=roman, paragraph_index=idx)
        for k, (idx, roman) in enumerate(body, 1)
        if ROMAN_TO_INT.get(roman) != k
    ]

    tail = find_index_start(paras)
    if tail is None or tail <= body[-1][0]:
        tail = len(paras)

    spans: dict[int, tuple[int, int]] = {}
    for k, (idx, _roman) in enumerate(body, 1):
        end = body[k][0] if k < N_CHAPTERS else tail
        spans[k] = (idx, end)
    return spans, anomalies


def multiset_agreement(a: list[str], b: list[str]) -> float:
    """語の多重集合としての一致(順序を無視する)。G-14 の判定に使う。"""
    if not a and not b:
        return 1.0
    shared = sum((Counter(a) & Counter(b)).values())
    return shared / max(len(a), len(b))


def sequence_agreement(a: list[str], b: list[str]) -> float:
    """語列としての一致(順序を含む)。参考値 —— 脚注の配置差で下がる。"""
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def chapter_agreements(
    do_paras: list[str], pg_paras: list[str], *, sequence: bool = True
) -> dict[int, Agreement]:
    """章ごとの二経路一致を返す(SPEC §10 G-14)。"""
    do_spans, _ = chapter_spans(do_paras)
    pg_spans, _ = chapter_spans(pg_paras)
    result: dict[int, Agreement] = {}
    for n in range(1, N_CHAPTERS + 1):
        a0, a1 = do_spans[n]
        b0, b1 = pg_spans[n]
        aw = norm_words(" ".join(do_paras[a0:a1]))
        bw = norm_words(" ".join(pg_paras[b0:b1]))
        result[n] = Agreement(
            chapter=n,
            words_a=len(aw),
            words_b=len(bw),
            sequence=sequence_agreement(aw, bw) if sequence else float("nan"),
            multiset=multiset_agreement(aw, bw),
        )
    return result
