import { getCollation, getIndexGold } from "@/lib/data";

const pct = (x: number) => `${(x * 100).toFixed(2)}%`;

export default function Home() {
  const c = getCollation();
  const g = getIndexGold();
  const t = c.totals;
  const passed = c.chapters.filter((x) => x.passes_gate).length;

  // 棒の幅は表の値そのものから引く(数値を画面側に決め打ちしない — SPEC G-11)
  const lo = Math.min(...c.chapters.map((x) => x.sequence)) - 0.02;
  const width = (v: number) => `${Math.max(0, (v - lo) / (1 - lo)) * 100}%`;

  return (
    <main>
      <h1>底本について</h1>
      <p className="lede">
        {c.work.author}『{c.work.title}』{c.work.edition}({c.work.publisher}, {c.work.year}
        )。Freeman 番号 {c.work.freeman}。原文はパブリックドメイン。
      </p>

      <p>
        本サイトは、この航海日誌を構造化データとして再構成する試みである。最初にやったのは、
        <strong>読む前に底本が正しいことを確かめること</strong>だった。
        同じ 1845 年版について、独立に翻刻された二つの電子テキストを突き合わせている。
      </p>

      <div className="scroll">
        <table>
          <caption>底本の二経路</caption>
          <thead>
            <tr>
              <th>ID</th>
              <th>役割</th>
              <th>経路</th>
              <th>sha256(先頭 12 桁)</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(c.sources).map(([id, s]) => (
              <tr key={id}>
                <td className="mono">S-{id}</td>
                <td>{s.role}</td>
                <td>{s.name}</td>
                <td className="mono">{s.sha256.slice(0, 12)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="note">
        <strong>版は書誌ではなく本文で確定した。</strong>
        配布元の書誌ページは 1839 年と表示するが、序文の日付と「largely condensed and corrected」の
        記述から 1845 年第2版である。メタデータを信じると版を取り違える。
        S-B については、配布元が付した前書き・後書き・商標表示を取り除き、
        パブリックドメインの本文のみを用いている。
      </div>

      <h2>二経路はどれだけ一致したか</h2>

      <ul className="stats">
        <li>
          <span className="k">語彙保存(順序無視)中央値</span>
          <span className="v">{pct(t.multiset_median)}</span>
        </li>
        <li>
          <span className="k">同 最小</span>
          <span className="v">{pct(t.multiset_min)}</span>
        </li>
        <li>
          <span className="k">一致率(順序込み)中央値</span>
          <span className="v">{pct(t.sequence_median)}</span>
        </li>
        <li>
          <span className="k">同 最小</span>
          <span className="v">{pct(t.sequence_min)}</span>
        </li>
      </ul>

      <p>
        この二つの差が結論である。<strong>語彙としては {pct(t.multiset_median)} 一致するのに、
        順序込みでは {pct(t.sequence_median)} に落ちる。</strong>
        原因は欠落ではなく並びで、片方は脚注を各章の末尾に集め、もう片方は頁上の位置に置いている。
        したがって品質ゲート {c.gate.id} の閾値は<strong>語彙保存に置き、順序込みの一致率には置かない</strong>
        —— 順序で {c.gate.threshold} を要求すると、正しい翻刻同士が落ちる。
      </p>

      <div className="scroll">
        <table>
          <caption>
            章別の一致(全 {t.chapters} 章 / ゲート {c.gate.id} 通過 {passed}/{t.chapters}、
            閾値は語彙保存 {c.gate.threshold})
          </caption>
          <thead>
            <tr>
              <th className="num">章</th>
              <th className="num">S-A 語数</th>
              <th className="num">S-B 語数</th>
              <th className="num">語彙保存</th>
              <th className="num">順序込み</th>
              <th>順序込みの水準</th>
            </tr>
          </thead>
          <tbody>
            {c.chapters.map((row) => (
              <tr key={row.chapter}>
                <td className="num">{row.chapter}</td>
                <td className="num">{row.words_a.toLocaleString("ja-JP")}</td>
                <td className="num">{row.words_b.toLocaleString("ja-JP")}</td>
                <td className="num">
                  {pct(row.multiset)}{" "}
                  <span className={row.passes_gate ? "tag tag--ok" : "tag tag--warn"}>
                    {row.passes_gate ? "通過" : "不通過"}
                  </span>
                </td>
                <td className="num">{pct(row.sequence)}</td>
                <td>
                  <span className="bar" style={{ width: width(row.sequence) }} aria-hidden="true" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>照合が見つけた翻刻の差</h2>

      <p>
        独立した二つの翻刻を突き合わせると、片方だけを読んでいては気づけない差が出る。
        見つけたものは<strong>黙って書き換えず</strong>、台帳に載せて検査が報告する形にしてある。
      </p>

      <div className="scroll">
        <table>
          <caption>既知の翻刻異常</caption>
          <thead>
            <tr>
              <th>ID</th>
              <th>側</th>
              <th>箇所</th>
              <th>観測</th>
              <th>あるべき値</th>
            </tr>
          </thead>
          <tbody>
            {c.ledger.map((e) => (
              <tr key={e.id}>
                <td className="mono">{e.id}</td>
                <td className="mono">{e.side}</td>
                <td>{e.where}</td>
                <td className="mono">{e.observed}</td>
                <td className="mono">{e.expected}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>総語数の差は、本文の差ではない</h2>

      <ul className="stats">
        <li>
          <span className="k">全体 S-A</span>
          <span className="v">{t.words_all_a.toLocaleString("ja-JP")}<span className="u">語</span></span>
        </li>
        <li>
          <span className="k">全体 S-B</span>
          <span className="v">{t.words_all_b.toLocaleString("ja-JP")}<span className="u">語</span></span>
        </li>
        <li>
          <span className="k">本文 {t.chapters} 章のみ S-A</span>
          <span className="v">{t.words_body_a.toLocaleString("ja-JP")}<span className="u">語</span></span>
        </li>
        <li>
          <span className="k">本文 {t.chapters} 章のみ S-B</span>
          <span className="v">{t.words_body_b.toLocaleString("ja-JP")}<span className="u">語</span></span>
        </li>
      </ul>

      <p>
        全体では {(t.words_all_a - t.words_all_b).toLocaleString("ja-JP")} 語も違うのに、
        <strong>本文だけで比べると差は {Math.abs(t.words_body_a - t.words_body_b).toLocaleString("ja-JP")} 語
        ({pct(Math.abs(t.words_body_a - t.words_body_b) / t.words_body_b)})</strong>しかない。
        差は全て章の外にある —— S-A は目次・索引・出版社広告を含み
        ({t.words_outside_chapters_a.toLocaleString("ja-JP")} 語)、S-B は含まない
        ({t.words_outside_chapters_b.toLocaleString("ja-JP")} 語)。
        <strong>数を比べるときは、それがどの母集団の数かを先に揃える。</strong>
      </p>

      <h2>この索引は誰も書いていない</h2>

      <p>
        S-A だけが 1845 年版の巻末索引を収録している。これは
        <strong>1845 年に人が編んだ「語 → 頁」の対応表</strong>で、
        本サイトも言語モデルも一行も書いていない。だから、本文から地名や事物を拾う仕掛けを
        あとで作ったとき、その出来をこの索引で測っても<strong>循環しない</strong>。
      </p>

      <ul className="stats">
        <li>
          <span className="k">項目</span>
          <span className="v">{g.counts.entries.toLocaleString("ja-JP")}</span>
        </li>
        <li>
          <span className="k">異なり見出し語</span>
          <span className="v">{g.counts.distinct_headwords.toLocaleString("ja-JP")}</span>
        </li>
        <li>
          <span className="k">頁参照</span>
          <span className="v">{g.counts.page_refs_expanded.toLocaleString("ja-JP")}</span>
        </li>
        <li>
          <span className="k">被覆頁数</span>
          <span className="v">{g.counts.pages_covered.toLocaleString("ja-JP")}</span>
        </li>
      </ul>

      <p>
        <a href="/index-gold/">索引を読む →</a>
      </p>

      <h2>配布</h2>
      <p>
        実測の生データは JSON で配っている。
        <a href="/data/collation.json">collation.json</a>(二経路照合)/{" "}
        <a href="/data/index_gold.json">index_gold.json</a>(索引)。
      </p>
    </main>
  );
}
