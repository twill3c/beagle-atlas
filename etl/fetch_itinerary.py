"""S-D(日次行程)を取得する。

**この資料はリポジトリに含めない。** Rookmaaker(2009)編の編纂物で著作権が生きており、
原文(1839 / 1845)や FitzRoy(1839)と扱いが違う。取得先は `raw/private/` で、
`.gitignore` に入れてある。配るのは、ここから導いた**事実**(日付・区分・座標)だけ。

    python -m etl.fetch_itinerary
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

URL = "https://darwin-online.org.uk/converted/Ancillary/Rookmaaker_Beagle_Itinerary_A575.html"
OUT = Path(__file__).resolve().parents[1] / "raw" / "private" / "itinerary_A575.html"
CITATION = (
    "Rookmaaker, Kees. 2009. Darwin's itinerary on the voyage of the Beagle. "
    "Edited by John van Wyhe. Darwin Online (A575)."
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "beagle-atlas/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    OUT.write_bytes(body)
    print(f"{OUT.relative_to(OUT.parents[2])} に保存({len(body):,} バイト)")
    print(f"  sha256 {hashlib.sha256(body).hexdigest()}")
    print(f"  出典 {CITATION}")
    print("  ※ この資料は再配布しない。派生する事実のみを data/ に出す")


if __name__ == "__main__":
    main()
