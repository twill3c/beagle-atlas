import { readFileSync } from "node:fs";
import { join } from "node:path";

export const metadata = {
  title: "二つの版 — ビーグル・アトラス",
  description:
    "1839 年初版と 1845 年第2版を突き合わせる。事前登録した主張は二つ通り、一つ落ちた。",
};

type Chapter = {
  chapter_1845: number;
  words_1845: number;
  words_1839_aligned: number;
  ratio: number | null;
  chapters_1839: number[];
};

type Diff = {
  preregistered: string;
  method: string;
  sources: Record<string, { chapters: number; sentences: number }>;
  alignment: { matching_blocks: number; matched_sentences: number; matched_pct_of_1845: number };
  totals: { words_1845: number; words_1839: number };
  chapters: Chapter[];
  gates: Record<string, { claim: string; passes: boolean; measured: Record<string, unknown> }>;
  verdict: string;
};

const GALAPAGOS = 17;

export default function EditionsPage() {
  const d: Diff = JSON.parse(
    readFileSync(join(process.cwd(), "data", "edition_diff.json"), "utf-8"),
  );
  const rows = d.chapters.filter((r) => r.ratio !== null);
  const ranked = [...rows].sort((a, b) => (b.ratio as number) - (a.ratio as number));
  const rank = new Map(ranked.map((r, i) => [r.chapter_1845, i + 1]));
  const gal = rows.find((r) => r.chapter_1845 === GALAPAGOS) as Chapter;
  const shrink = (1 - d.totals.words_1845 / d.totals.words_1839) * 100;
  const maxRatio = Math.max(...rows.map((r) => r.ratio as number));

  return (
    <main>
      <h1>二つの版</h1>
      <p className="lede">
        『ビーグル号航海記』には 1839 年の初版と 1845 年の第 2 版がある。
        第 2 版は全体としては<strong>縮んでいる</strong>。では、どこが削られ、どこが残ったのか。
      </p>

      <div className="note">
        <p style={{ marginTop: 0 }}>
          <strong>この測定は、結果を見る前に主張と閾値を書いて登録してある。</strong>
          {d.preregistered}。対象の第 {GALAPAGOS} 章も、差分を一度も走らせる前に
          章見出しから特定して固定した。
        </p>
        <p style={{ marginBottom: 0 }}>
          主張は「<strong>縮んだ版で、そこだけ膨らんだ</strong>」——
          全体が減る中でガラパゴスの範囲だけは増えており、しかもその増加は突出する、というもの。
        </p>
      </div>

      <h2>判定</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>主張</th>
              <th>実測</th>
              <th>判定</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="mono">G-20a</td>
              <td>本文全体の語数が減る</td>
              <td className="num">
                {d.totals.words_1845.toLocaleString("ja-JP")} &lt;{" "}
                {d.totals.words_1839.toLocaleString("ja-JP")}(−{shrink.toFixed(1)}%)
              </td>
              <td><span className="tag tag--ok">通過</span></td>
            </tr>
            <tr>
              <td className="mono">G-20b</td>
              <td>ガラパゴスの範囲の語数が増える</td>
              <td className="num">比 {gal.ratio?.toFixed(3)}</td>
              <td><span className="tag tag--ok">通過</span></td>
            </tr>
            <tr>
              <td className="mono">G-20c</td>
              <td>その増加率が全範囲中で上位 3 位以内</td>
              <td className="num">{rank.get(GALAPAGOS)} 位 / {ranked.length}</td>
              <td><span className="tag tag--warn">不通過</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="note note--warn">
        <p style={{ marginTop: 0 }}>
          <strong>総合判定: {d.verdict}。</strong>
          「縮んだ」も「そこだけ膨らんだ」も成り立ったが、「突出する」は成り立たなかった。
        </p>
        <p style={{ marginBottom: 0 }}>
          閾値は 3 位以内で、実測は {rank.get(GALAPAGOS)} 位。
          <strong>1 つ違いだが、順位の閾値は緩めない</strong> ——
          それは登録した時点で決めてある。書ける結論は
          「<strong>増えてはいるが、突出はしない</strong>」である。
        </p>
      </div>

      <h2>章ごとの増減</h2>
      <p>
        1845 年版は 21 章、1839 年版は 23 章で<strong>章番号は 1 対 1 に対応しない</strong>。
        そこで章番号で突き合わせず、文の単位で二版を整列し、
        1845 年版の各章に対応する 1839 年側の範囲を整列から決めている。
      </p>
      <div className="scroll">
        <table>
          <caption>比 = 1845 年版の語数 ÷ 対応する 1839 年側の語数。1.0 より大きければ増えている</caption>
          <thead>
            <tr>
              <th className="num">1845 章</th>
              <th className="num">1845 語数</th>
              <th className="num">1839 語数</th>
              <th className="num">比</th>
              <th className="num">順位</th>
              <th>増減</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isGal = r.chapter_1845 === GALAPAGOS;
              const ratio = r.ratio as number;
              return (
                <tr key={r.chapter_1845} style={isGal ? { fontWeight: 600 } : undefined}>
                  <td className="num">
                    {r.chapter_1845}
                    {isGal && <span className="tag" style={{ marginLeft: ".4rem" }}>ガラパゴス</span>}
                  </td>
                  <td className="num">{r.words_1845.toLocaleString("ja-JP")}</td>
                  <td className="num">{r.words_1839_aligned.toLocaleString("ja-JP")}</td>
                  <td className="num">{ratio.toFixed(3)}</td>
                  <td className="num">{rank.get(r.chapter_1845)}</td>
                  <td>
                    <span
                      className="bar"
                      style={{
                        width: `${(ratio / maxRatio) * 100}%`,
                        background: ratio > 1 ? "var(--land)" : "var(--sea)",
                      }}
                      aria-hidden="true"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h2>計器について</h2>
      <p className="small">
        文の一致は 1845 年版の {d.alignment.matched_pct_of_1845}%
        ({d.alignment.matched_sentences.toLocaleString("ja-JP")} 文 /
        {" "}{d.alignment.matching_blocks.toLocaleString("ja-JP")} ブロック)。
        二版で語句が改められているため、これ以上は上がらない。
        <strong>4 位と 3 位を分けた差は、この精度に支えられていない</strong> ——
        順位の細かい差を主張の根拠にはしない。
      </p>
      <p className="small">
        最初の実装は 1839 側の範囲を「一致した文の最小・最大」で取っており、
        アンカーの疎な章で比が跳ね上がっていた(第 9 章 2.32・第 20 章 2.30)。
        章の境目を隣接アンカーの中点に置く分割に直し、
        <strong>1839 年版の総語数が保存されることを検算に入れた</strong>。
        ガラパゴスの順位は両方式とも {rank.get(GALAPAGOS)} 位で動かなかったが、
        動かないことは直して測るまで分からなかった。
      </p>
      <p className="small">
        生データ: <a href="/data/edition_diff.json">edition_diff.json</a>
      </p>
    </main>
  );
}
