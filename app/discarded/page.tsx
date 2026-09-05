import { readFileSync } from "node:fs";
import { join } from "node:path";

export const metadata = {
  title: "測って、捨てた — ビーグル・アトラス",
  description:
    "言えると思って測り、言えなかったことの記録。閾値は先に置き、外れても動かさない。",
};

type Record_ = {
  id: string;
  kind: "claim" | "premise";
  registered: string;
  judged: string;
  title: string;
  claim: string;
  threshold: string;
  measured: string;
  verdict: string;
  distance: string;
  why_it_matters: string;
  what_we_did_not_do: string;
  source: string;
  page: string;
};

type Discarded = {
  policy: string;
  counts: { total: number; claims: number; premises: number };
  records: Record_[];
};

export default function DiscardedPage() {
  const d: Discarded = JSON.parse(
    readFileSync(join(process.cwd(), "data", "discarded.json"), "utf-8"),
  );

  return (
    <main>
      <h1>測って、捨てた</h1>
      <p className="lede">
        言えると思って測り、言えなかったことの記録。
        このサイトがいちばん確かに持っているのは、たぶんこの頁である。
      </p>

      <div className="note">
        <p style={{ marginTop: 0 }}>
          このサイトは<strong>目玉を追わない</strong>。図は標準的なものだけを出し、
          凝った主張のための図は作らない。{d.policy}
        </p>
        <p style={{ marginBottom: 0 }}>
          三つ目の主張を立てて当てにいくこともできた。やらないのは、
          <strong>当たるまで探す動きになると、外れた二件の記録の価値まで薄れる</strong>からである。
        </p>
      </div>

      <h2>やり方</h2>
      <ol className="rules">
        <li>
          <strong>測る前に、主張と閾値を書いて日付を打つ。</strong>
          データを見てから閾値を決めれば、どんな主張でも通る。
        </li>
        <li>
          <strong>外れても閾値を動かさない。</strong>
          後から動かせるなら、先に書いたことは何も担保しない。
        </li>
        <li>
          <strong>物差しを取り替えて救わない。</strong>
          別の測り方なら通る、はたいてい本当だが、それは別の主張である。
        </li>
        <li>
          <strong>落ちた主張を画面から消さない。</strong>
          消せば、残った主張だけが並んだ、実態より強い顔のサイトになる。
        </li>
      </ol>

      <h2>記録({d.counts.claims} 件の主張と {d.counts.premises} 件の前提)</h2>

      {d.records.map((r) => (
        <article key={r.id} className="discard">
          <header className="discard__head">
            <span className="mono discard__id">{r.id}</span>
            <h3>{r.title}</h3>
            <span className={r.verdict === "撤回" ? "tag tag--warn" : "tag tag--warn"}>
              {r.verdict}
            </span>
          </header>

          <p className="discard__claim">{r.claim}</p>

          <dl className="discard__grid">
            <div>
              <dt>登録</dt>
              <dd className="mono">{r.registered}</dd>
            </div>
            <div>
              <dt>閾値</dt>
              <dd>{r.threshold}</dd>
            </div>
            <div>
              <dt>実測</dt>
              <dd className="mono">{r.measured}</dd>
            </div>
            <div>
              <dt>判定</dt>
              <dd className="mono">
                {r.judged} — {r.verdict}
              </dd>
            </div>
          </dl>

          <p className="small">{r.distance !== "—" && <><strong>どれくらい外れたか。</strong>{r.distance}。</>}</p>
          <p>{r.why_it_matters}</p>
          <p className="discard__restraint">
            <strong>やらなかったこと。</strong>
            {r.what_we_did_not_do}
          </p>
          <p className="small">
            出所 <code>{r.source}</code> ／ <a href={r.page}>該当ページを見る</a>
          </p>
        </article>
      ))}

      <h2>これは何のための頁か</h2>
      <p>
        古典を扱ったサイトは、たいてい「分かったこと」だけを並べる。
        だが実際に測ると、言えることは思ったより少ない。
        <strong>その少なさを隠さずに出すほうが、資料に対して誠実だと考えている。</strong>
      </p>
      <p>
        ここに並んだ三件は、いずれも<strong>測らなければ気づけなかった</strong>ことでもある。
        印象では航海記はずっと陸を歩いているように読めるし、
        ガラパゴスの章が特別に手を入れられたという話には筋が通っている。
        測って初めて、どちらも「そこまでは言えない」と分かった。
      </p>
      <p className="small">
        生データ: <a href="/data/discarded.json">discarded.json</a>
      </p>
    </main>
  );
}
