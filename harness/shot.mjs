// 図を一度だけ目で見るための撮影。代理指標が全部緑でも、はみ出し・切れ・重なりは
// 描画してからでないと分からない。`node harness/shot.mjs <path> <出力先> [幅]`
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { chromium } from "playwright";

const ROOT = new URL("../out/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const path = process.argv[2] ?? "/";
const outFile = process.argv[3] ?? "shot.png";
const width = Number(process.argv[4] ?? 1280);
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
    const file = join(ROOT, normalize(p).replace(/^[/\\]+/, ""));
    const body = await readFile(file);
    res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404).end("not found");
  }
});

await new Promise((r) => server.listen(0, r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 1100 } });
await page.goto(base + path, { waitUntil: "networkidle" });
await page.screenshot({ path: outFile, fullPage: true });
await browser.close();
server.close();
console.log(`撮影 ${path} @${width} → ${outFile}`);
