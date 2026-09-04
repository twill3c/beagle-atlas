"""1845 年版索引のパース(SPEC §7 O-1b)。

索引は「1845 年に人が編んだ 語 → 頁 の対応表」であり、抽出器の gold として使う。
LLM も本プロジェクトも一行も書いていないので、抽出の評価が循環しない。

実データが教えた三つの癖(2026-09-04 に全域を走査してから実装した — HC-069):

1. **終端は印刷されている。** 索引の末尾に `THE END.` があり、以降は印刷所の奥付と
   出版社広告。辞書順や頁範囲から終端を推定する必要はない
2. **辞書順は成り立たない。** 下位項目は整列されておらず、さらに **J の項目群が I より前**
   に来る(1845 年の組版に見られる I/J 合併配列)。検査は頭文字の水準でのみ行う
3. **継続行 `———` は直前の見出し語を継承する**

分類できない行は黙って捨てず `UnclassifiedLine` で止める(AGENTS.md)。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

KINDS = ("headword", "continuation")

# 継続行の頭(em ダッシュの連なり)。ハイフン・en ダッシュも受ける
CONTINUATION_RE = re.compile(r"^[—–-]{2,}\s*")

# 行末の頁参照ブロック: 「12」「12, 34」「246 to 251」「187, 224, 246 to 251」「35—38」
# 範囲には二つの表記がある(2026-09-04 実測: `N to M` 12 行 / `N—M` 2 行)。
_RANGE_SEP = r"(?:\s+to\s+|\s*[—–]\s*)"
_PAGE_TOKEN = rf"\d{{1,3}}(?:{_RANGE_SEP}\d{{1,3}})?"
PAGE_BLOCK_RE = re.compile(rf",?\s*((?:{_PAGE_TOKEN})(?:\s*,\s*{_PAGE_TOKEN})*)\s*\.?\s*$")
RANGE_RE = re.compile(rf"^(\d{{1,3}}){_RANGE_SEP}(\d{{1,3}})$")

SEE_RE = re.compile(r"\bsee\b\s+(.+?)\s*\.?$", re.I)
END_MARK_RE = re.compile(r"^THE\s+END\.?$", re.I)
INDEX_HEAD_RE = re.compile(r"^INDEX\.?$")


class UnclassifiedLine(ValueError):
    """索引の行がどの型にも当たらなかった。黙って捨てず、ここで止める。"""


@dataclass(frozen=True)
class IndexEntry:
    line: int
    raw: str
    kind: str
    headword: str
    subentry: str | None
    pages: tuple[int, ...]
    ranges: tuple[tuple[int, int], ...]
    see: str | None

    @property
    def term(self) -> str:
        return f"{self.headword}, {self.subentry}" if self.subentry else self.headword

    @property
    def all_pages(self) -> tuple[int, ...]:
        """個別頁と範囲を展開した頁集合。"""
        out = set(self.pages)
        for a, b in self.ranges:
            out.update(range(a, b + 1))
        return tuple(sorted(out))


def is_end_mark(text: str) -> bool:
    return bool(END_MARK_RE.match(text.strip()))


def find_index_body(paras: list[str]) -> tuple[int, int]:
    """索引本体の [start, end) を返す。end は `THE END.` の位置。"""
    heads = [i for i, p in enumerate(paras) if INDEX_HEAD_RE.match(p.strip())]
    if not heads:
        raise UnclassifiedLine("索引の見出し `INDEX.` が見つからない")
    start = heads[-1] + 1
    for i in range(start, len(paras)):
        if is_end_mark(paras[i]):
            return start, i
    raise UnclassifiedLine("索引の終端標識 `THE END.` が見つからない")


def _split_pages(text: str) -> tuple[str, tuple[int, ...], tuple[tuple[int, int], ...]]:
    """行末の頁参照ブロックを切り出し、(本文部, 個別頁, 範囲) を返す。"""
    m = PAGE_BLOCK_RE.search(text)
    if not m:
        return text.strip(), (), ()
    pages: list[int] = []
    ranges: list[tuple[int, int]] = []
    for token in m.group(1).split(","):
        token = token.strip()
        if not token:
            continue
        r = RANGE_RE.match(token)
        if r:
            ranges.append((int(r.group(1)), int(r.group(2))))
        else:
            pages.append(int(token))
    return text[: m.start()].strip(), tuple(pages), tuple(ranges)


def parse_index(paras: list[str]) -> list[IndexEntry]:
    """索引本体を項目列にする。行と項目は 1:1(取りこぼしを作らない)。"""
    start, end = find_index_body(paras)
    entries: list[IndexEntry] = []
    current_headword: str | None = None

    for i in range(start, end):
        raw = paras[i]
        text = raw.strip()
        if not text:
            raise UnclassifiedLine(f"[{i}] 空行は索引の型に当たらない: {raw!r}")

        cont = CONTINUATION_RE.match(text)
        if cont:
            if current_headword is None:
                raise UnclassifiedLine(f"[{i}] 継承する見出し語が無い継続行: {raw!r}")
            kind = "continuation"
            body = text[cont.end() :].lstrip(", ").strip()
            headword = current_headword
        else:
            kind = "headword"
            body = text
            headword = None  # 下で決める

        # 複合項目: `Galapagos Archipelago, 372; natural history of, 377` のように
        # セミコロンで区切られ、**区切りごとに頁参照を持つ**行がある。
        # 行末だけを見ると前半の頁が黙って落ちる(2026-09-04 に独立再計算が検出)。
        texts: list[str] = []
        pages_acc: list[int] = []
        ranges_acc: list[tuple[int, int]] = []
        for segment in body.split(";"):
            seg_text, seg_pages, seg_ranges = _split_pages(segment.strip())
            if seg_text:
                texts.append(seg_text)
            pages_acc.extend(seg_pages)
            ranges_acc.extend(seg_ranges)
        body = "; ".join(texts)
        pages, ranges = tuple(pages_acc), tuple(ranges_acc)

        see = None
        if not pages and not ranges:
            m = SEE_RE.search(body)
            if m:
                see = m.group(1).strip()
                body = body[: m.start()].rstrip(", ").strip()

        if kind == "headword":
            head, _, rest = body.partition(",")
            headword = head.strip()
            subentry = rest.strip().rstrip(".,") or None
            if not headword:
                raise UnclassifiedLine(f"[{i}] 見出し語を取り出せない: {raw!r}")
            current_headword = headword
        else:
            subentry = body.rstrip(".,") or None

        if not (pages or ranges or see):
            raise UnclassifiedLine(f"[{i}] 頁参照も相互参照も持たない行: {raw!r}")

        entries.append(
            IndexEntry(
                line=i,
                raw=raw,
                kind=kind,
                headword=headword,
                subentry=subentry,
                pages=pages,
                ranges=ranges,
                see=see,
            )
        )
    return entries


def out_of_range_refs(
    entries: list[IndexEntry], lo: int, hi: int
) -> list[tuple[int, int]]:
    """本の頁範囲 [lo, hi] を外れる頁参照を (行, 頁) で返す。"""
    bad: list[tuple[int, int]] = []
    for e in entries:
        for p in e.all_pages:
            if not lo <= p <= hi:
                bad.append((e.line, p))
    return bad


def first_letter_inversions(entries: list[IndexEntry]) -> list[tuple[str, str]]:
    """見出し行の頭文字が後退した箇所を (直前までの最大, 現在) で返す。

    **下位項目は整列されていないので、検査は頭文字の水準でのみ行う。**
    1845 年版では J の項目群が I より前に来るため、正常な索引でも ('J', 'I') が出る。
    """
    found: list[tuple[str, str]] = []
    running = ""
    for e in entries:
        if e.kind != "headword" or not e.headword:
            continue
        c = e.headword[0].upper()
        if not c.isalpha():
            continue
        if c < running:
            pair = (running, c)
            if pair not in found:
                found.append(pair)
        running = max(running, c)
    return found
