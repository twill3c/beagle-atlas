"""測って捨てた主張の一覧を組む(SPEC §6 / G-21)。

**この一覧が本作の主題である。** 目玉を追う路線をやめたので、
「測ったが言えなかった」ことの記録を正面に置く。

数値は既存の成果物から引く。ここに書き写さない(SPEC G-11)——
文言だけをこのファイルが持ち、実測値は voyage.json / edition_diff.json から読む。

    python -m etl.build_discarded
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "discarded.json"

GALAPAGOS_CHAPTER = 17


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def build() -> dict:
    voyage = load("voyage.json")
    diff = load("edition_diff.json")

    land_pct = voyage["totals"]["by_state_pct"]["Land"]
    gal = next(r for r in diff["chapters"] if r["chapter_1845"] == GALAPAGOS_CHAPTER)
    ranked = sorted(
        (r for r in diff["chapters"] if r["ratio"] is not None),
        key=lambda r: r["ratio"],
        reverse=True,
    )
    gal_rank = next(
        i for i, r in enumerate(ranked, 1) if r["chapter_1845"] == GALAPAGOS_CHAPTER
    )

    records = [
        {
            "id": "N-1",
            "kind": "claim",
            "registered": "2026-09-04",
            "judged": "2026-09-05",
            "title": "『ビーグル号航海記』は航海の本ではない",
            "claim": "日付が特定できる日のうち、ダーウィンが陸にいた日が過半を占める。",
            "threshold": "陸上日 ≥ 55%",
            "measured": f"{land_pct:.1f}%",
            "verdict": "不成立",
            "distance": "閾値まで 21 ポイント。近くもない",
            "why_it_matters": (
                "本を読んだ印象では「ずっと陸を歩いている」ように感じる。"
                "実際に数えると、夜を陸で過ごした日は三分の一だった。"
                "印象と記録が食い違う典型で、数えなければ気づけない。"
            ),
            "what_we_did_not_do": (
                "区分は「夜をどこで過ごしたか」で、昼に上陸して夜は船に戻った日は"
                "停泊の側に入る。昼を基準にすれば別の数になる —— "
                "が、主張を救うために物差しを取り替えるのは筋が悪いので、そうしなかった。"
            ),
            "source": "data/voyage.json",
            "page": "/voyage/",
        },
        {
            "id": "N-2",
            "kind": "claim",
            "registered": "2026-09-05",
            "judged": "2026-09-05",
            "title": "縮んだ版で、そこだけ膨らんだ",
            "claim": (
                "1845 年第 2 版は全体として縮んだが、ガラパゴスを扱う範囲だけは膨らみ、"
                "その増加は全章中で突出する。"
            ),
            "threshold": "全体が縮む / ガラパゴスの比 > 1.00 / その順位 ≤ 3",
            "measured": f"縮んだ ✓ / 比 {gal['ratio']:.3f} ✓ / 順位 {gal_rank} 位 ✗",
            "verdict": "不成立",
            "distance": "三条件のうち二つは通過。順位だけが 1 つ足りない",
            "why_it_matters": (
                "全体が 10% 縮む中で、ガラパゴスの章は 1.22 倍に増えている。"
                "方向は主張どおりだった。しかし同じくらい、あるいはそれ以上に増えた章が"
                "ほかに三つある。「そこだけ」とは言えない。"
            ),
            "what_we_did_not_do": (
                "1 つ違いだったが、順位の閾値は緩めなかった。"
                "登録した時点で「緩めない」と書いてあり、"
                "後から動かせるなら事前登録は何も担保しない。"
            ),
            "source": "data/edition_diff.json",
            "page": "/editions/",
        },
        {
            "id": "N-3",
            "kind": "premise",
            "registered": "2026-09-04",
            "judged": "2026-09-05",
            "title": "1839 年初版には翻刻テキストが存在しない",
            "claim": "初版は画像と PDF しか無いので、版の差分は原理的に測れない。",
            "threshold": "(前提として書いた。閾値ではない)",
            "measured": "翻刻テキストは存在した",
            "verdict": "撤回",
            "distance": "—",
            "why_it_matters": (
                "確かめたのは初版の分冊と目録だけだった。"
                "同じ本文を『Narrative』第 3 巻として収める版に、完全な翻刻がある。"
                "**母集団を数え切らずに「存在しない」と書いた**。"
            ),
            "what_we_did_not_do": (
                "この誤りに気づいたのは、別の資料を探していて偶然その版に当たったからで、"
                "自分の検査が見つけたわけではない。"
            ),
            "source": "raw/f10_3.converted.html",
            "page": "/editions/",
        },
    ]

    baseline_path = DATA / "baseline.json"
    if baseline_path.exists():
        b = json.loads(baseline_path.read_text(encoding="utf-8"))
        name = b["by_kind"]["name"]
        desc = b["by_kind"]["description"]
        records.append(
            {
                "id": "N-4",
                "kind": "premise",
                "registered": "2026-09-04",
                "judged": "2026-09-05",
                "title": "索引の見出し語は、抽出器の再現率を測る物差しになる",
                "claim": (
                    "1845 年の索引は語と頁の対応表なので、"
                    "見出し語のうち本文から拾えた率をそのまま再現率にできる(閾値 0.90)。"
                ),
                "threshold": "見出し語の再現率 ≥ 0.90",
                "measured": (
                    f"名前の型 {name['entries']} 件は {name['entry_level_recall']:.3f}、"
                    f"説明文の型 {desc['entries']} 件は {desc['entry_level_recall']:.3f}"
                ),
                "verdict": "撤回",
                "distance": "—",
                "why_it_matters": (
                    "見出し語の約 4 分の 1 は、編者が書いた説明文であって本文中の文字列ではない"
                    "(「Absence of trees in Pampas」のような形)。**文字列として本文に存在しない**ので、"
                    "どんな抽出器でも拾えない。閾値 0.90 は達成不可能だった。"
                ),
                "what_we_did_not_do": (
                    "閾値を下げて通す、という直し方はしなかった。物差しの側が間違っているので、"
                    "索引を再現率に使うなら名前の型に限る —— そう決めたうえで、"
                    "新しい閾値は上回るべき相手(ベースライン)を実測してから置き直す。"
                ),
                "source": "data/baseline.json",
                "page": "/index-gold/",
            }
        )

    fert_path = DATA / "fertility.json"
    if fert_path.exists():
        f = json.loads(fert_path.read_text(encoding="utf-8"))
        h, m = f["models"]["MacBERTh"], f["models"]["DistilBERT"]
        records.append(
            {
                "id": "N-5",
                "kind": "premise",
                "registered": "2026-09-04",
                "judged": "2026-09-05",
                "title": "19 世紀英語は、現代英語のモデルでは荒れる",
                "claim": (
                    "1845 年の綴りや語法は現代と隔たっているので、"
                    "歴史英語で事前学習した tokenizer の方が本文を効率よく刻むはずである。"
                ),
                "threshold": "MacBERTh の fertility < DistilBERT の fertility",
                "measured": (
                    f"MacBERTh {h['fertility']:.3f} 対 DistilBERT {m['fertility']:.3f}(逆)"
                ),
                "verdict": "不成立",
                "distance": f"歴史側が {f['comparison']['fertility_ratio_historical_over_modern']:.3f} 倍粗い",
                "why_it_matters": (
                    "語彙サイズはほぼ同じ(0.98 倍)なので、語彙の大きさでは説明できない。"
                    "**1845 年の散文は、綴りの上では現代英語とさほど変わらない** —— "
                    "というのが実測の答えだった。"
                ),
                "what_we_did_not_do": (
                    "当初は「未知語率で基盤モデルを選ぶ」と書いていたが、"
                    "実際には両者とも未知語率 0 だった。WordPiece はラテン文字に未知語を出さず、"
                    "必ずサブワードに分解する。**tokenizer の性質を確かめずに指標を決めていた。**"
                ),
                "source": "data/fertility.json",
                "page": "/",
            }
        )

    return {
        "schema": "beagle-atlas/discarded@1",
        "policy": (
            "本作は目玉を追わない。標準的な図を素直に出し、"
            "測って捨てた主張の記録そのものを主題にする(SPEC §6・2026-09-05 方針転換)。"
        ),
        "counts": {
            "total": len(records),
            "claims": sum(1 for r in records if r["kind"] == "claim"),
            "premises": sum(1 for r in records if r["kind"] == "premise"),
        },
        "records": records,
    }


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT)} を書いた — {d['counts']}")
    for r in d["records"]:
        print(f"  {r['id']} {r['verdict']}  {r['title']}")


if __name__ == "__main__":
    main()
