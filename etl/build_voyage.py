"""S-D から航海の**事実**だけを取り出す(SPEC §3・O-3)。

出す: 日番号・暦日・その日の区分(海上 / 停泊 / 上陸)・座標。
出さない: 出典の記述文・地名注記。**編纂物の複製にしないため**、
表現にあたる部分は一切写さない。事実そのものに著作権は及ばない。

    python -m etl.build_voyage
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import date
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

# SPEC G-06。帆走の物理限界 10 ノット = 10 × 1.852 km/h × 24 h
SHIP_KM_PER_DAY = 10 * 1.852 * 24

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "private" / "itinerary_A575.html"
OUT = ROOT / "data" / "voyage.json"

CITATION = (
    "Rookmaaker, Kees. 2009. Darwin's itinerary on the voyage of the Beagle. "
    "Edited by John van Wyhe. Darwin Online (A575)."
)

DAY_RE = re.compile(
    r"^Day\s+(?P<n>\d{1,4})\s*[–—-]\s*\w{3}\s*[–—-]\s*"
    r"(?P<date>\d{1,2}\s+\w{3}\s+\d{4})\s*[–—-]\s*\((?P<cat>[^)]*)\)(?P<rest>.*)$"
)
# 「45º32' N 9º30' W」の形。度分のみで秒は無い(実測 2026-09-05)
COORD_RE = re.compile(
    r"(?P<la>\d{1,3})º\s*(?P<lam>\d{1,2})'\s*(?P<ns>[NS])"
    r"[^0-9]{0,6}"
    r"(?P<lo>\d{1,3})º\s*(?P<lom>\d{1,2})'\s*(?P<ew>[EW])"
)
MONTHS = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
CATEGORIES = ("Sea", "Harbour", "Land")


def paragraphs(path: Path) -> list[str]:
    s = path.read_bytes().decode("utf-8", "replace")
    out = []
    for b in re.findall(r"<p\b[^>]*>(.*?)</p>", s, re.S | re.I):
        t = re.sub(r"<[^>]+>", " ", b)
        t = html.unescape(t)
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            out.append(t)
    return out


def parse_date(text: str) -> str:
    d, mon, y = text.split()
    if mon not in MONTHS:
        raise ValueError(f"月名を解せない: {text!r}")
    return date(int(y), MONTHS[mon], int(d)).isoformat()


def parse_coord(text: str) -> tuple[float, float] | None:
    m = COORD_RE.search(text)
    if not m:
        return None
    lat = int(m.group("la")) + int(m.group("lam")) / 60
    lon = int(m.group("lo")) + int(m.group("lom")) / 60
    if m.group("ns") == "S":
        lat = -lat
    if m.group("ew") == "W":
        lon = -lon
    # 仮定が崩れたらここで落ちる(黙って通る道を残さない)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"座標が範囲外: {lat} {lon} ← {text[:60]!r}")
    return round(lat, 4), round(lon, 4)


def haversine_km(a: dict, b: dict) -> float:
    """大円距離(km)。地球半径 6371 km。"""
    la1, lo1, la2, lo2 = (radians(x) for x in (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * asin(min(1.0, sqrt(h)))


def flag_speed_outliers(days: list[dict]) -> list[dict]:
    """帆走の物理限界(SPEC G-06: 10 ノット)を超える座標を外れ値として印す。

    **前後の両方に対して超える点だけを外れ値とする。** 片側だけなら、
    速いのはその点ではなく隣の点かもしれない。資料には実際に誤記がある ——
    day 207 は前後が 50º59'W と 53º19'W なのに 05º17'W(2026-09-05 実測)。

    印すだけで**捨てない**。件数を出し、地図では線を繋がない。
    """
    pts = [d for d in days if d["lat"] is not None]
    for i, d in enumerate(pts):
        prev_bad = next_bad = False
        if i > 0:
            gap = max(1, d["day"] - pts[i - 1]["day"])
            prev_bad = haversine_km(pts[i - 1], d) / gap > SHIP_KM_PER_DAY
        if i < len(pts) - 1:
            gap = max(1, pts[i + 1]["day"] - d["day"])
            next_bad = haversine_km(d, pts[i + 1]) / gap > SHIP_KM_PER_DAY
        # 端の点は片側しか見られないので、その片側で判定する
        d["speed_outlier"] = (prev_bad and next_bad) if 0 < i < len(pts) - 1 else (prev_bad or next_bad)
    for d in days:
        d.setdefault("speed_outlier", False)
    return [d for d in pts if d["speed_outlier"]]


def flag_speed_legs(days: list[dict]) -> list[dict]:
    """区間側の違反。**点に帰属できなくても「ここは何かおかしい」は言える。**

    「前後の両方で違反」の点だけを見ると、階段状のずれを見逃す ——
    day 1490→1491 は 1 日で 33 度(約 3,000 km)動くが、1491 以降が一貫しているため
    点としては外れ値にならない(2026-09-05 実測)。地図ではこの区間の線を繋がない。
    """
    pts = [d for d in days if d["lat"] is not None]
    bad = []
    for a, b in zip(pts, pts[1:]):
        gap = max(1, b["day"] - a["day"])
        km = haversine_km(a, b)
        if km / gap > SHIP_KM_PER_DAY:
            bad.append(
                {
                    "from_day": a["day"],
                    "to_day": b["day"],
                    "from_date": a["date"],
                    "to_date": b["date"],
                    "km": round(km),
                    "days": gap,
                    "km_per_day": round(km / gap),
                }
            )
    return bad


def build() -> dict:
    if not SRC.exists():
        raise SystemExit(
            "S-D が無い。`python -m etl.fetch_itinerary` で取得すること"
            "(この資料は再配布しないためリポジトリに含めていない)"
        )
    days = []
    for line in paragraphs(SRC):
        m = DAY_RE.match(line)
        if not m:
            continue
        cat = m.group("cat").strip()
        if cat not in CATEGORIES:
            raise ValueError(f"未知の区分 {cat!r}(既知: {CATEGORIES})")
        coord = parse_coord(m.group("rest"))
        days.append(
            {
                "day": int(m.group("n")),
                "date": parse_date(m.group("date")),
                "state": cat,
                "lat": coord[0] if coord else None,
                "lon": coord[1] if coord else None,
            }
        )

    # --- 検算(仮定が崩れたら落ちる)
    nums = [d["day"] for d in days]
    if nums != list(range(1, len(days) + 1)):
        missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
        raise ValueError(f"日番号が連続しない。欠番 {missing[:10]}")
    dates = [d["date"] for d in days]
    if dates != sorted(dates):
        raise ValueError("暦日が単調でない")
    # 日付境界の越えで暦日が 1 日飛ぶ箇所があるのは既知(SPEC L1-4)
    gaps = [
        (a, b)
        for a, b in zip(dates, dates[1:])
        if (date.fromisoformat(b) - date.fromisoformat(a)).days != 1
    ]

    outliers = flag_speed_outliers(days)
    bad_legs = flag_speed_legs(days)
    counts = Counter(d["state"] for d in days)
    with_coord = sum(1 for d in days if d["lat"] is not None)
    return {
        "schema": "beagle-atlas/voyage@1",
        "provenance": {
            "source_id": "S-D",
            "citation": CITATION,
            "note": (
                "この資料は 2009 年の編纂物で著作権があるため再配布しない。"
                "ここに出すのは日付・区分・座標という事実のみで、記述文は含まない。"
            ),
        },
        "totals": {
            "days": len(days),
            "first_date": dates[0],
            "last_date": dates[-1],
            "by_state": {k: counts[k] for k in CATEGORIES},
            "by_state_pct": {k: round(counts[k] / len(days) * 100, 1) for k in CATEGORIES},
            "days_with_coord": with_coord,
            "calendar_gaps": [{"from": a, "to": b} for a, b in gaps],
            "speed_limit_km_per_day": round(SHIP_KM_PER_DAY, 1),
            "speed_outliers": [
                {"day": d["day"], "date": d["date"], "lat": d["lat"], "lon": d["lon"]}
                for d in outliers
            ],
            "speed_bad_legs": bad_legs,
        },
        "days": days,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    t = data["totals"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  {t['days']:,} 日 / {t['first_date']} – {t['last_date']}")
    print(f"  区分 {t['by_state']}  ({t['by_state_pct']})")
    print(f"  座標つき {t['days_with_coord']:,} 日 / 暦日の飛び {len(t['calendar_gaps'])} 箇所")


if __name__ == "__main__":
    main()
