# beagle-atlas — ビーグル・アトラス

ダーウィン『ビーグル号航海記』(*Journal of Researches*, 2nd ed., 1845)を、
**航海日誌の構造化データ**として再構成し、地理と時間の二軸から本文へ再入場させる。

- 主画面: 世界地図上の航路(船の航跡と人の足跡を別系列で描く)
- 副画面: 年表(1831–1836)とテキストペイン
- **cron ゼロ・関数ゼロの完全静的配信**。データは 1836 年で確定しており更新されない

詳細は [SPEC.md](SPEC.md) を参照。テストの規約とオラクルの出所は [TEST_SPEC.md](TEST_SPEC.md)。

## 底本

Charles Darwin, *Journal of Researches into the Natural History and Geology of the Countries
Visited during the Voyage of H.M.S. Beagle round the World*, 2nd ed.
(London: John Murray, 1845). Freeman 番号 **F14**。原文はパブリックドメイン。

電子テキストは **Darwin Online の翻刻(F14)を正本**とし、**Project Gutenberg 電子書籍 #944**
のプレーンテキストを第二経路として突合している。後者については配布元が付した前書き・後書き・
商標表示を取り除き、パブリックドメインの本文のみを用いている。

取得日・バイト数・sha256・加工手順は [`raw/MANIFEST.json`](raw/MANIFEST.json) に固定してある。

**版は書誌メタデータではなく本文で確定した。** 配布元の書誌ページは 1839 年と表示するが、
序文の日付と「largely condensed and corrected」の記述から 1845 年第 2 版である。

## 二経路照合が見つけたもの(L0・2026-09-04)

独立した二つの翻刻を突き合わせることで、片方だけを読んでいては気づけない差が出た。

| ID | 側 | 箇所 | 観測 |
|---|---|---|---|
| E-01 | Darwin Online | 本文 第 20 章 見出し | `CHAPTER XXX.`(正しくは `CHAPTER XX.`) |
| E-02 | Darwin Online | 序文の署名 | 日の数字と地名行を欠く |

いずれも**黙って書き換えず**、台帳に載せて検査が報告する形にしてある。

一致の水準:

| 指標 | 値 |
|---|---|
| 語彙保存(多重集合・順序無視) | 中央値 **0.9911** / 最小 0.9494 |
| 一致率(順序込み) | 中央値 0.9542 / 最小 0.8759 |

差は**欠落ではなく並び**である。Project Gutenberg 版は脚注を章末に集め、
Darwin Online 版は頁上の位置に置く。したがって
**品質ゲート G-14 の閾値は語彙保存に置き、順序込みの一致率には置かない**。

## 開発

```bash
python -m pytest -q          # テスト
python harness/text_hygiene.py   # 字種・制御文字の検査
```

## ライセンス

コードは [LICENSE](LICENSE) を参照。原文(1845 年刊)はパブリックドメイン。
