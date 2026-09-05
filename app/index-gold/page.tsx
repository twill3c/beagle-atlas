import { IndexBrowser } from "@/components/IndexBrowser";
import { IndexDensity } from "@/components/IndexDensity";
import { getIndexGold } from "@/lib/data";
import { getFigures } from "@/lib/figures";

export const metadata = {
  title: "1845 年版の索引 — ビーグル・アトラス",
  description:
    "1845 年第2版の巻末索引を構造化したもの。語 → 頁の対応表として、本文から事物を拾う仕掛けの評価に使う。",
};

export default function IndexGoldPage() {
  const g = getIndexGold();
  const fig = getFigures().index_density;
  const [lo, hi] = g.checks.book_page_bounds;

  return (
    <main>
      <h1>1845 年版の索引</h1>
      <p className="lede">{g.provenance}</p>

      <ul className="stats">
        <li>
          <span className="k">項目</span>
          <span className="v">{g.counts.entries.toLocaleString("ja-JP")}</span>
        </li>
        <li>
          <span className="k">見出し / 下位</span>
          <span className="v">
            {g.counts.headwords.toLocaleString("ja-JP")}
            <span className="u">/ {g.counts.continuations.toLocaleString("ja-JP")}</span>
          </span>
        </li>
        <li>
          <span className="k">異なり見出し語</span>
          <span className="v">{g.counts.distinct_headwords.toLocaleString("ja-JP")}</span>
        </li>
        <li>
          <span className="k">頁参照(範囲展開後)</span>
          <span className="v">{g.counts.page_refs_expanded.toLocaleString("ja-JP")}</span>
        </li>
        <li>
          <span className="k">被覆頁数</span>
          <span className="v">{g.counts.pages_covered.toLocaleString("ja-JP")}</span>
        </li>
        <li>
          <span className="k">範囲外の頁参照</span>
          <span className="v">{g.checks.out_of_range_refs.length}</span>
        </li>
      </ul>

      <h2>この索引を読むときに知っておくこと</h2>

      <p>
        機械的に切り出すにあたって、実データが三つのことを教えた。いずれも推測で書けば外していた。
      </p>

      <h3>終端は本が印刷している</h3>
      <p>
        索引の末尾には <code>{g.boundaries.end_marker}</code> があり、以降は印刷所の奥付と
        出版社の広告が続く。{g.boundaries.note}
        辞書順や頁範囲から終端を推定する必要はなかった。
      </p>

      <h3>並びは辞書順ではない</h3>
      <p>
        下位項目は整列されていない。さらに<strong>J の項目群が I より前に来る</strong> ——
        1845 年の組版に見られる I/J 合併配列である。実際、頭文字の逆転は全体で
        {g.checks.first_letter_inversions.length} 箇所だけで、それが
        {g.checks.first_letter_inversions.map((p) => ` ${p[0]} → ${p[1]}`).join(" ")} である。
        {g.checks.inversion_note}
        素朴な辞書順検査は、正しい索引の方を落とす。
      </p>

      <h3>頁範囲の表記は一つではない</h3>
      <p>
        個別の頁のほかに範囲があり、その書き方は二通りある(<code>N to M</code> と{" "}
        <code>N—M</code>)。加えて、緯度の表記に現れる数は頁ではない。
        行末だけを見る実装はこれらを静かに取りこぼす —— 実際に取りこぼしていた。
        いまは「行に現れる頁参照を一つも落とさない」という不変量で固定してある。
        全 {g.counts.page_refs_expanded.toLocaleString("ja-JP")} 件の頁参照は、
        すべて本の頁範囲 {lo}–{hi} に収まっている。
      </p>

      <h2>索引が指した頁</h2>
      <p>
        1845 年の編者が、本のどの頁を何回指したか。
        <strong>選んだのは当時の編者であって、本サイトではない。</strong>
        {fig.total_refs_in_body.toLocaleString("ja-JP")} 件の参照が本文
        {fig.page_from}–{fig.page_to} 頁に収まり、本文の外を指すものは
        {fig.refs_outside_body} 件だった。1 頁あたり最大 {fig.max_refs_on_a_page} 件、
        一度も指されなかった頁は {fig.pages_with_no_ref} 頁ある。
      </p>
      <IndexDensity fig={fig} />

      <div className="scroll">
        <table>
          <caption>章ごとの索引参照(頁あたり)</caption>
          <thead>
            <tr>
              <th className="num">章</th>
              <th className="num">頁</th>
              <th className="num">頁数</th>
              <th className="num">参照</th>
              <th className="num">頁あたり</th>
            </tr>
          </thead>
          <tbody>
            {fig.by_chapter.map((c) => (
              <tr key={c.chapter}>
                <td className="num">{c.chapter}</td>
                <td className="num">{c.page_from}–{c.page_to}</td>
                <td className="num">{c.pages}</td>
                <td className="num">{c.refs}</td>
                <td className="num">{c.refs_per_page.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>索引</h2>
      <p className="lede">
        見出し語で絞り込める。数字だけを入れると、その頁を参照している項目が出る。
      </p>

      <IndexBrowser entries={g.entries} />

      <p style={{ marginTop: "2rem" }}>
        生データ: <a href="/data/index_gold.json">index_gold.json</a>
      </p>
    </main>
  );
}
