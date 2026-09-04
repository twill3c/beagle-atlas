// data/*.json を public/data/ へ写す。配布(SPEC F-09)と、画面からの直リンク用。
// ビルドのたびに走るので、data/ が正で public/ は生成物である。
import { cp, mkdir, readdir, rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "data");
const DEST = join(ROOT, "public", "data");

await rm(DEST, { recursive: true, force: true });
await mkdir(DEST, { recursive: true });

const files = (await readdir(SRC)).filter((f) => f.endsWith(".json"));
if (files.length === 0) {
  console.error("data/ に JSON が無い。先に `npm run data` を実行すること");
  process.exit(1);
}
for (const f of files) {
  await cp(join(SRC, f), join(DEST, f));
}
console.log(`public/data/ へ ${files.length} 件写した: ${files.join(", ")}`);
