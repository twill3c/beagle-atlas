import { readFileSync } from "node:fs";
import { join } from "node:path";

export const metadata = {
  title: "読む — ビーグル・アトラス",
  description:
    "1845 年第2版の本文を段落ごとに原文と和訳で並べる。訳の巧拙は主張せず、充填率だけを出す。",
};

type Item = { id: string; seq: number; words: number; text: string };
type Chapter = { chapter: number; title: string; summary: string; paragraphs: number; words: number; items: Item[] };
type Text = { totals: { chapters: number; paragraphs: number; words: number }; chapters: Chapter[] };
type Trans = {
  policy: string;
  totals: { translated: number; paragraphs_total: number; fill_rate: number; by_chapter: Record<string, number> };
  items: Record<string, string>;
};

const read = <T,>(name: string): T =>
  JSON.parse(readFileSync(join(process.cwd(), "data", name), "utf-8")) as T;

export default function ReadPage() {
  const text = read<Text>("text.json");
  const tr = read<Trans>("translations.json");
  // 訳のある章だけを出す。未訳の章まで原文で並べても読み物にならない
  const shown = text.chapters.filter((c) => (tr.totals.by_chapter[`c${String(c.chapter).padStart(2, "0")}`] ?? 0) > 0);

  return (
    <main>
      <h1>読む</h1>
      <p className="lede">
        底本の本文を段落ごとに原文と和訳で並べる。訳は自前で、
        <strong>巧拙は主張しない</strong> —— 出すのは充填率と、原文の何が落ちていないかだけ。
      </p>

      <ul className="stats">
        <li>
          <span className="k">訳した段落</span>
          <span className="v">
            {tr.totals.translated}
            <span className="u">/ {tr.totals.paragraphs_total.toLocaleString("ja-JP")}</span>
          </span>
        </li>
        <li>
          <span className="k">充填率</span>
          <span className="v">{(tr.totals.fill_rate * 100).toFixed(1)}<span className="u">%</span></span>
        </li>
        <li>
          <span className="k">訳した章</span>
          <span className="v">{shown.length}<span className="u">/ {text.totals.chapters}</span></span>
        </li>
      </ul>

      <div className="note">
        <p style={{ marginTop: 0 }}>{tr.policy}</p>
        <p style={{ marginBottom: 0 }}>
          検査は「原文の何が落ちたか」だけを見る —— <strong>数(距離・高度・脚注番号)が
          訳文にそのまま現れること</strong>と、段落が原文と 1 対 1 であること。
          訳の良し悪しは測っていないので、<strong>この検査を通っても訳が良いとは言えない</strong>。
        </p>
      </div>

      {shown.map((c) => (
        <section key={c.chapter}>
          <h2>
            第 {c.chapter} 章 —— {c.title}
          </h2>
          <p className="small">
            {c.paragraphs} 段落 / {c.words.toLocaleString("ja-JP")} 語。
            見出しの要約行(著者側が章の話題を列挙したもの):
          </p>
          <p className="chapter-summary">{c.summary}</p>

          {c.items.map((it) => {
            const ja = tr.items[it.id];
            return (
              <article key={it.id} className="para" id={it.id}>
                <div className="para__meta">
                  <a href={`#${it.id}`} className="mono">{it.id}</a>
                  <span className="small">{it.words} 語</span>
                  {!ja && <span className="tag tag--warn">未訳</span>}
                </div>
                <div className="para__cols">
                  <p className="para__src" lang="en">{it.text}</p>
                  {ja ? <p className="para__ja">{ja}</p> : null}
                </div>
              </article>
            );
          })}
        </section>
      ))}

      <h2>まだ訳していないもの</h2>
      <p>
        残りは {(tr.totals.paragraphs_total - tr.totals.translated).toLocaleString("ja-JP")} 段落。
        <strong>全訳を公開の前提にはしていない。</strong>
        訳した段落から順に並べ、未訳の章はこの画面に出さない。
        途中で止まっても、出ているものが壊れることはない。
      </p>
      <p className="small">
        生データ: <a href="/data/text.json">text.json</a> ／{" "}
        <a href="/data/translations.json">translations.json</a>
      </p>
    </main>
  );
}
