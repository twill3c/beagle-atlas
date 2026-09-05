"""FitzRoy の気象日誌から気温と水温を取り出す(SPEC §3 S-C)。

出典は FitzRoy, *Narrative* vol. II の Appendix(F10.2a・1839 年刊・パブリックドメイン)。
月ごとの気象表が並んでおり、日・時・風・気圧・気温・水温・地名の 12 列を持つ。

取り出すのは**数値の事実**(暦日・気温・水温)と、地点の短い名前だけ。
標準的な集計であり、主張ではない(SPEC §6 の路線)。

数の書式に注意: 小数点が中黒(`30·29` / `71·5`)である。

    python -m etl.build_weather
"""
from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "f10_2a.converted.html"
OUT = ROOT / "data" / "weather.json"

MONTHS = {
    m.upper(): i
    for i, m in enumerate(
        "January February March April May June July August September October "
        "November December".split(), 1
    )
}
# 月ラベルの区切りは不揃いである(実測 2026-09-05):
#   `JANUARY, 1832.` / `FEBRUARY,1834.` / `APRIL,1834` / `OCTOBER.1834.`
# コンマ・ピリオド・空白のいずれか、あるいは何も無い場合がある。
# 「たいていコンマ+空白」で書くと 7 か月ぶんを黙って落とす。
MONTH_RE = re.compile(r"^([A-Z]+)[,.]?\s*(\d{4})\.?$")
# 気温は華氏。航海の範囲(氷点下の南氷洋〜熱帯)を大きく外れたら誤読とみなす
TEMP_MIN, TEMP_MAX = 10.0, 110.0


def cells(row: str) -> list[str]:
    out = []
    for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, re.S | re.I):
        x = re.sub(r"<[^>]+>", " ", c)
        x = html.unescape(x)
        out.append(re.sub(r"\s+", " ", x).strip())
    return out


def num(text: str) -> float | None:
    """`71·5` のような中黒の小数を読む。読めなければ None。"""
    t = text.replace("·", ".").replace("‧", ".").strip()
    if not re.fullmatch(r"-?\d{1,3}(\.\d+)?", t):
        return None
    return float(t)


def build() -> dict:
    src = SRC.read_text(encoding="utf-8", errors="replace")
    tables = re.findall(r"<table\b.*?</table>", src, re.S | re.I)

    records: list[dict] = []
    months_seen: set[str] = set()
    skipped_tables = 0
    meteo_tables = 0
    unread_meteo: list[str] = []
    for t in tables:
        rows = [cells(r) for r in re.findall(r"<tr\b.*?</tr>", t, re.S | re.I)]
        head = " ".join(" ".join(r) for r in rows[:2])
        is_meteo = "Temp. Water" in head or "Temp. Air" in head
        if is_meteo:
            meteo_tables += 1
        if len(rows) < 3 or not rows[0] or rows[0][0].rstrip(".").lower() != "day":
            skipped_tables += 1
            if is_meteo:
                unread_meteo.append("先頭セルが Day でない")
            continue
        m = next(
            (MONTH_RE.match(c) for r in rows[1:3] for c in r if MONTH_RE.match(c)), None
        )
        if not m or m.group(1) not in MONTHS:
            skipped_tables += 1
            if is_meteo:
                # 実測 2026-09-05: 1 表だけ月ラベルに年が無い(`DECEMBER.`)。
                # 前後から 1831 年と推測できるが、**黙って推測せず読めなかったものとして数える**。
                label = next((c for r in rows[1:3] for c in r if c and c.isupper()), "(不明)")
                unread_meteo.append(f"月ラベルに年が無い: {label}")
            continue
        month, year = MONTHS[m.group(1)], int(m.group(2))
        months_seen.add(f"{year:04d}-{month:02d}")

        for r in rows:
            if len(r) < 11:
                continue
            day = num(r[0])
            if day is None or not 1 <= day <= 31:
                continue
            air, water = num(r[8]), num(r[9])
            if air is None and water is None:
                continue
            try:
                d = date(year, month, int(day)).isoformat()
            except ValueError:
                continue  # その月に存在しない日付
            rec = {"date": d, "locality": r[10].rstrip(".") or None}
            if air is not None and TEMP_MIN <= air <= TEMP_MAX:
                rec["air_f"] = air
            if water is not None and TEMP_MIN <= water <= TEMP_MAX:
                rec["water_f"] = water
            if "air_f" in rec or "water_f" in rec:
                records.append(rec)

    if not records:
        raise ValueError("気象表を 1 件も読めなかった。表の形が変わった疑い")
    records.sort(key=lambda r: r["date"])

    # 月ごとの平均(標準図はこの粒度で出す)
    by_month: dict[str, dict[str, list[float]]] = {}
    for r in records:
        k = r["date"][:7]
        b = by_month.setdefault(k, {"air": [], "water": []})
        if "air_f" in r:
            b["air"].append(r["air_f"])
        if "water_f" in r:
            b["water"].append(r["water_f"])
    monthly = [
        {
            "month": k,
            "air_mean_f": round(sum(v["air"]) / len(v["air"]), 1) if v["air"] else None,
            "water_mean_f": round(sum(v["water"]) / len(v["water"]), 1) if v["water"] else None,
            "n_air": len(v["air"]),
            "n_water": len(v["water"]),
        }
        for k, v in sorted(by_month.items())
    ]

    airs = [r["air_f"] for r in records if "air_f" in r]
    waters = [r["water_f"] for r in records if "water_f" in r]
    return {
        "schema": "beagle-atlas/weather@1",
        "source": {
            "id": "S-C",
            "name": "FitzRoy, Narrative of the surveying voyages… vol. II, Appendix (1839)",
            "file": SRC.name,
            "copyright_status": "public domain",
            "note": "取り出したのは暦日・気温・水温・地点名のみ。単位は華氏。",
        },
        "totals": {
            "records": len(records),
            "months_with_table": len(months_seen),
            "meteorological_tables": meteo_tables,
            "meteorological_tables_unread": unread_meteo,
            "tables_skipped": skipped_tables,
            "first_date": records[0]["date"],
            "last_date": records[-1]["date"],
            "air_readings": len(airs),
            "water_readings": len(waters),
            "air_min_f": min(airs) if airs else None,
            "air_max_f": max(airs) if airs else None,
            "water_min_f": min(waters) if waters else None,
            "water_max_f": max(waters) if waters else None,
        },
        "monthly": monthly,
        "records": records,
    }


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    t = d["totals"]
    print(f"{OUT.relative_to(ROOT)} を書いた")
    print(f"  観測 {t['records']:,} 件 / {t['first_date']} – {t['last_date']}"
          f" / 表を読めた月 {t['months_with_table']} / 飛ばした表 {t['tables_skipped']}")
    print(f"  気温 {t['air_readings']:,} 件 {t['air_min_f']}–{t['air_max_f']}°F"
          f" / 水温 {t['water_readings']:,} 件 {t['water_min_f']}–{t['water_max_f']}°F")
    print(f"  月平均の行 {len(d['monthly'])}")


if __name__ == "__main__":
    main()
