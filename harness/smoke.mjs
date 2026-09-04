// 出荷物を実ブラウザで検品する(SPEC N-03 / G-11)。
// 静的検査では見つからない型の欠陥 —— 横溢れ・固定フッタの重なり・クライアント側の絞り込み ——
// を、実際に描画して確かめる。out/ を素の静的サーバで配り、chromium で開く。
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { chromium } from "playwright";

const ROOT = new URL("../out/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const WIDTHS = [320, 390, 768, 1280];
const PAGES = ["/", "/index-gold/"];
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
};

const server = createServer(async (req, res) => {
  try {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p.endsWith("/")) p += "index.html";
    const file = join(ROOT, normalize(p).replace(/^([/\\])+/, ""));
    const body = await readFile(file);
    res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404).end("not found");
  }
});

await stat(join(ROOT, "index.html")).catch(() => {
  console.error("out/ が無い。先に `npm run build` を実行すること");
  process.exit(2);
});

await new Promise((r) => server.listen(0, r));
const base = `http://127.0.0.1:${server.address().port}`;
const failures = [];
const check = (ok, msg) => { if (!ok) failures.push(msg); };

const browser = await chromium.launch();
try {
  for (const path of PAGES) {
    for (const width of WIDTHS) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      const res = await page.goto(base + path, { waitUntil: "networkidle" });
      check(res?.status() === 200, `${path} @${width}: HTTP ${res?.status()}`);

      // N-03 横溢れ
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      check(overflow <= 1, `${path} @${width}: 横溢れ ${overflow}px`);

      // フッタが下部固定で見えていて、本文の末尾を隠していない
      const footer = await page.evaluate(() => {
        const el = document.querySelector(".site-footer");
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        const pad = parseFloat(getComputedStyle(document.body).paddingBottom);
        return { position: cs.position, bottom: r.bottom, h: r.height, pad, vh: innerHeight };
      });
      check(footer !== null, `${path} @${width}: フッタが無い`);
      if (footer) {
        check(footer.position === "fixed", `${path} @${width}: フッタが fixed でない`);
        check(
          Math.abs(footer.bottom - footer.vh) <= 1,
          `${path} @${width}: フッタが下端にない (${footer.bottom} vs ${footer.vh})`,
        );
        check(
          footer.pad >= footer.h,
          `${path} @${width}: body の逃げ ${footer.pad}px < フッタ高 ${footer.h}px`,
        );
      }
      check(errors.length === 0, `${path} @${width}: JS エラー ${errors[0] ?? ""}`);
      await page.close();
    }
  }

  // 索引の絞り込みが実際に効く(クライアント側の挙動なので静的検査では見えない)
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(base + "/index-gold/", { waitUntil: "networkidle" });
  const before = await page.locator(".entries li").count();
  await page.fill('input[type="search"]', "Galapagos");
  await page.waitForFunction(
    (n) => document.querySelectorAll(".entries li").length < n,
    before,
    { timeout: 5000 },
  );
  const after = await page.locator(".entries li").count();
  check(before > 1000, `索引の初期表示が ${before} 件しかない`);
  check(after > 0 && after < before, `絞り込みが効いていない (${before} → ${after})`);

  // 陽性対照: 当たらない語では 0 件になる
  await page.fill('input[type="search"]', "zzzznotfound");
  await page.waitForFunction(() => document.querySelectorAll(".entries li").length === 0, null, {
    timeout: 5000,
  });
  await page.close();
} finally {
  await browser.close();
  server.close();
}

if (failures.length) {
  console.error(`検品 NG — ${failures.length} 件`);
  for (const f of failures) console.error("  -", f);
  process.exit(1);
}
console.log(`検品 OK — ${PAGES.length} ページ × ${WIDTHS.length} 幅 + 絞り込みの挙動`);
