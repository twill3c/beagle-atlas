# -*- coding: utf-8 -*-
"""本番が手元のビルドと同じものを配っているかを確かめる。

    python harness/check_prod.py [パス ...]

**バイト長の一致は一致ではない。** Vercel はリモートで再ビルドするので、
Next.js のビルド ID と資産ハッシュだけが必ず変わる。そこを正規化してから
本文を突き合わせる。

**踏んだ罠(loop_017)**: 本番では同じビルド ID が
`<!--aWoqKMdkll_bY4h01f8o2-->` と `\\"b\\":\\"aWoqKMdkll-bY4h01f8o2\\"` の
二通りで現れ、11 文字目が `_` と `-` で食い違う。手元のビルドでは両者が
一致するので、**片方だけを置換する比較は手元では通り本番でだけ落ちる**。
それゆえ ID は「見つけたものを全部」集めて置換する。

差が出たら最初の食い違いを前後ごと出す。**黙って緑にしない。**

Git Bash から引数でパスを渡すときは `MSYS_NO_PATHCONV=1` を付ける。
付けないと `/read/` が `C:/Program Files/Git/read/` に化ける。
引数なしなら既定のパスを Python 側で持つので影響を受けない。
"""
from __future__ import annotations

import hashlib
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://beagle-atlas.vercel.app"
DEFAULT_PATHS = ["/", "/read/", "/index-gold/", "/voyage/", "/editions/", "/discarded/"]

ID_PATTERNS = (
    re.compile(r"<!--([A-Za-z0-9_-]{21})-->"),          # 先頭のコメント
    re.compile(r'\\"b\\":\\"([A-Za-z0-9_-]{21})\\"'),   # RSC ペイロード
)


def local_path(path: str) -> Path:
    rel = path.strip("/")
    return ROOT / "out" / (f"{rel}/index.html" if rel else "index.html")


def build_ids(s: str) -> set[str]:
    out: set[str] = set()
    for pat in ID_PATTERNS:
        out |= set(pat.findall(s))
    return out


def normalize(s: str) -> str:
    for i in sorted(build_ids(s), key=len, reverse=True):
        s = s.replace(i, "BUILDID")
    s = re.sub(r"/_next/static/[A-Za-z0-9_-]+/", "/_next/static/HASH/", s)
    return re.sub(r"[a-f0-9]{16}\.js", "HASH.js", s)


def first_diff(a: str, b: str) -> str:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            lo, hi = max(0, i - 70), i + 70
            return f"    offset {i}\n    本番: {a[lo:hi]!r}\n    手元: {b[lo:hi]!r}"
    return f"    長さだけが違う: 本番 {len(a)} / 手元 {len(b)}"


def main() -> int:
    paths = sys.argv[1:] or DEFAULT_PATHS
    bad = 0
    for path in paths:
        lp = local_path(path)
        if not lp.exists():
            print(f"NG {path} — 手元に {lp.relative_to(ROOT)} がない(先に npm run build)")
            bad += 1
            continue
        with urllib.request.urlopen(BASE + path, timeout=60) as r:
            if r.status != 200:
                print(f"NG {path} — HTTP {r.status}")
                bad += 1
                continue
            prod = r.read().decode("utf-8")
        loc = lp.read_text(encoding="utf-8")
        a, b = normalize(prod), normalize(loc)
        if a == b:
            print(f"OK {path} — {len(prod.encode()):,} バイト / 正規化後 sha256 {hashlib.sha256(a.encode()).hexdigest()[:16]}")
        else:
            print(f"NG {path} — ビルド ID を除いても一致しない")
            print(first_diff(a, b))
            bad += 1
    print(f"\n{len(paths) - bad}/{len(paths)} ページが手元のビルドと一致")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
