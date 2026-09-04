"""航海データの検査(G-06 速度制約 / G-08 決定性)。

期待値の出所は各ケースのコメントに記す。S-D(日次行程)は 2009 年の編纂物で
著作権があるため配布物には含めず、ここで検査するのは
そこから導いた**事実**(日付・区分・座標)だけである。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VOYAGE = ROOT / "data" / "voyage.json"

pytestmark = pytest.mark.skipif(
    not VOYAGE.exists(), reason="data/voyage.json が無い(python -m etl.build_voyage で作る)"
)


@pytest.fixture(scope="session")
def voyage():
    return json.loads(VOYAGE.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_t050_day_numbers_are_contiguous(voyage):
    """T-050: 日番号が 1 から連続する(実測 2026-09-05: 1–1,740・欠番なし)。

    件数は定数で書かず「連続している」という不変量で書く(HC-016)。
    """
    days = [d["day"] for d in voyage["days"]]
    assert days == list(range(1, len(days) + 1))


@pytest.mark.unit
def test_t051_states_are_from_the_known_set(voyage):
    """T-051: 区分が既知の三種に収まる。未知の値は黙って通さない。"""
    seen = {d["state"] for d in voyage["days"]}
    assert seen <= {"Sea", "Harbour", "Land"}, f"未知の区分: {seen - {'Sea', 'Harbour', 'Land'}}"
    assert seen == {"Sea", "Harbour", "Land"}, "三区分すべてが現れるはず"


@pytest.mark.unit
def test_t052_g06_speed_gate_is_applied(voyage):
    """T-052(G-06): 帆走の物理限界を超える区間が数えられ、記録されている。

    出所: SPEC §10 G-06(10 ノット = 1 日 444.5 km)。
    **ゲートが「適用された」ことを検査する** —— 違反 0 件でも、
    ゲートが動いていないのか本当に 0 件なのかを区別できなければ意味がない。
    """
    t = voyage["totals"]
    assert t["speed_limit_km_per_day"] == pytest.approx(10 * 1.852 * 24, abs=0.1)
    assert "speed_bad_legs" in t and "speed_outliers" in t
    # 実測 2026-09-05: 資料には実際に誤記があり、違反区間が見つかっている。
    # ここが 0 件になったら、資料が直ったかゲートが壊れたかのどちらかで、どちらも要調査。
    assert len(t["speed_bad_legs"]) > 0, "違反 0 件。資料が直ったかゲートが働いていない"
    for leg in t["speed_bad_legs"]:
        assert leg["km_per_day"] > t["speed_limit_km_per_day"]


@pytest.mark.unit
def test_t053_g06_positive_control_slow_leg_passes():
    """T-053(G-06): 陽性対照の裏 —— 妥当な速度の区間は違反にならない。

    ゲートが「何にでも撃つ」わけではないことを確かめる(G-10)。
    """
    from etl.build_voyage import SHIP_KM_PER_DAY, haversine_km

    # プリマス付近から 1 日で約 200 km 南下した想定(緯度 1.8 度 ≈ 200 km)
    a = {"lat": 50.0, "lon": -4.0}
    b = {"lat": 48.2, "lon": -4.0}
    assert haversine_km(a, b) / 1 < SHIP_KM_PER_DAY

    # 同じ距離を 1 日で 10 倍動けば違反になる
    far = {"lat": 50.0, "lon": 24.0}
    assert haversine_km(a, far) / 1 > SHIP_KM_PER_DAY


@pytest.mark.validation
def test_t054_g08_etl_is_deterministic(tmp_path):
    """T-054(G-08): 同一入力・同一 seed で ETL の出力が bit 一致する。

    出所: SPEC §10 G-08。実際に二度作って突き合わせる。
    """
    before = VOYAGE.read_bytes()
    r = subprocess.run(
        [sys.executable, "-m", "etl.build_voyage"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert VOYAGE.read_bytes() == before, "二度目の生成が一度目と一致しない"
