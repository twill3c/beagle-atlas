"""19 世紀英語に対する tokenizer の fertility を測る(SPEC §5 M-3)。

問い: **歴史英語で事前学習したモデルは、この本文を現代英語のモデルより効率よく刻むか。**

fertility = サブワード数 ÷ 空白区切りの語数。小さいほど、その語彙が本文に合っている。
学習も推論もしない —— tokenizer だけを当てる。

**交絡を先に断っておく。** fertility は語彙サイズの関数でもある。語彙が大きければ
時代が合っていなくても下がりうるので、語彙サイズを併記しなければ比較にならない。

    .venv/Scripts/python -m etl.build_fertility
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from etl import sources

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "f14.converted.html"
OUT = ROOT / "data" / "fertility.json"

MODELS = {
    "MacBERTh": {
        "id": "emanjavacas/MacBERTh",
        "note": "1450–1950 年の歴史英語で事前学習(Manjavacas & Fonteyn)",
        "era": "historical",
    },
    "DistilBERT": {
        "id": "distilbert-base-uncased",
        "note": "現代英語で事前学習",
        "era": "modern",
    },
}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


def body_words() -> list[str]:
    """1845 年版の本文 21 章から、英字の語だけを取り出す。"""
    paras, _ = sources.load_darwin_online(SRC)
    spans, _ = sources.chapter_spans(paras)
    words: list[str] = []
    for n in range(1, sources.N_CHAPTERS + 1):
        a, b = spans[n]
        for p in paras[a:b]:
            words.extend(WORD_RE.findall(p))
    return words


def measure(name: str, spec: dict, words: list[str]) -> dict:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(spec["id"])
    pieces = 0
    split = 0
    unk = 0
    unk_id = tok.unk_token_id
    # 語ごとに刻む。文をまとめて刻むと、語の境目が fertility に混ざる
    for w in words:
        ids = tok.encode(w, add_special_tokens=False)
        if not ids:
            continue
        pieces += len(ids)
        if len(ids) > 1:
            split += 1
        if unk_id is not None and unk_id in ids:
            unk += 1
    n = len(words)
    return {
        "model": spec["id"],
        "era": spec["era"],
        "note": spec["note"],
        "vocab_size": tok.vocab_size,
        "words": n,
        "subwords": pieces,
        "fertility": round(pieces / n, 4),
        "words_split": split,
        "split_rate": round(split / n, 4),
        "words_with_unk": unk,
        "unk_rate": round(unk / n, 6),
    }


def build() -> dict:
    words = body_words()
    rows = {name: measure(name, spec, words) for name, spec in MODELS.items()}
    hist = rows["MacBERTh"]
    modern = rows["DistilBERT"]
    return {
        "schema": "beagle-atlas/fertility@1",
        "question": (
            "歴史英語で事前学習した tokenizer は、この 1845 年の本文を"
            "現代英語のものより効率よく刻むか。"
        ),
        "method": (
            "1845 年版本文 21 章から英字の語を取り出し、語ごとに刻んで"
            "サブワード数 ÷ 語数を測る。学習も推論もしない。"
        ),
        "caveat": (
            "fertility は語彙サイズの関数でもある。語彙が大きければ時代が合っていなくても"
            "下がりうるので、語彙サイズを併記しなければ比較にならない。"
        ),
        "corpus": {"source": SRC.name, "chapters": sources.N_CHAPTERS, "words": len(words)},
        "models": rows,
        "comparison": {
            "fertility_ratio_historical_over_modern": round(
                hist["fertility"] / modern["fertility"], 4
            ),
            "vocab_ratio_historical_over_modern": round(
                hist["vocab_size"] / modern["vocab_size"], 4
            ),
        },
    }


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT)} を書いた / 語 {d['corpus']['words']:,}")
    for name, r in d["models"].items():
        print(
            f"  {name:11} fertility {r['fertility']:.3f} / 分割率 {r['split_rate']:.3f}"
            f" / 語彙 {r['vocab_size']:,} / UNK 率 {r['unk_rate']}"
        )
    c = d["comparison"]
    print(f"  歴史 ÷ 現代: fertility {c['fertility_ratio_historical_over_modern']}"
          f" / 語彙 {c['vocab_ratio_historical_over_modern']}")


if __name__ == "__main__":
    main()
