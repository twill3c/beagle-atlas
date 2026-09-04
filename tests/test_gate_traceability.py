"""SPEC の品質ゲートと、それを確かめる検査の対応(HC-157)。

SPEC のゲート表は**宣言であって、実装でも検査でもない**。`G-xx` を書いた時点で
守られていると錯覚しやすく、テストは自分が書いた分しか主張しないので、
**書き忘れたゲートについては誰も沈黙を破らない**。

そこで対応そのものを検査する。各 `G-xx` は次のどちらかでなければならない:

  (a) tests/ か TEST_SPEC.md から ID で参照されている
  (b) SPEC 側に「未実装」と明記されている

実際にこれを書いて初めて、`G-06` を SPEC に書きながら航路に当てていなかったことに
気づけた(2026-09-05)。
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "SPEC.md"
TEST_SPEC = ROOT / "TEST_SPEC.md"
TESTS = ROOT / "tests"

GATE_ID = re.compile(r"\bG-\d{2}[a-z]?\b")
# SPEC の品質ゲート表の行。先頭セルが G-xx のもの
GATE_ROW = re.compile(r"^\|\s*\*{0,2}(G-\d{2}[a-z]?)\*{0,2}\s*\|(?P<rest>.*)$", re.M)
UNIMPLEMENTED = "未実装"


def declared_gates() -> dict[str, str]:
    """SPEC のゲート表から {ID: 行の残り} を採る。"""
    text = SPEC.read_text(encoding="utf-8")
    return {m.group(1): m.group("rest") for m in GATE_ROW.finditer(text)}


def referenced_gates() -> set[str]:
    """tests/ と TEST_SPEC.md が ID で言及しているゲート。"""
    found: set[str] = set()
    for p in [TEST_SPEC, *sorted(TESTS.glob("*.py"))]:
        if p.name == Path(__file__).name:
            continue  # 自分自身の言及は参照に数えない
        found |= set(GATE_ID.findall(p.read_text(encoding="utf-8")))
    return found


@pytest.mark.unit
def test_spec_declares_gates():
    """走査対象が空でないこと(検査が働いていることの確認)。"""
    gates = declared_gates()
    assert len(gates) >= 5, f"ゲートが {len(gates)} 件しか採れない。表の書式が変わった疑い"


@pytest.mark.unit
def test_every_gate_is_traced_or_marked_unimplemented():
    """T-040: 宣言したゲートは、検査されるか「未実装」と明記されるかのどちらか。"""
    gates = declared_gates()
    refs = referenced_gates()
    orphans = {
        gid: rest.strip()[:60]
        for gid, rest in gates.items()
        if gid not in refs and UNIMPLEMENTED not in rest
    }
    assert not orphans, (
        "宣言されているが、検査もされず「未実装」とも書かれていないゲート:\n"
        + "\n".join(f"  {k}: {v}" for k, v in sorted(orphans.items()))
    )


@pytest.mark.unit
def test_positive_control_orphan_gate_is_caught():
    """T-041: 陽性対照。参照も「未実装」も無いゲートを検査が撃つ。

    これが撃たなければ、T-040 の緑は「対応が取れている」ことと
    「検査が働いていない」ことを区別できない(G-10)。
    """
    gates = {"G-99": " 実在しない対照用のゲート | 閾値 |"}
    refs: set[str] = set()
    orphans = [
        gid for gid, rest in gates.items() if gid not in refs and UNIMPLEMENTED not in rest
    ]
    assert orphans == ["G-99"]

    # 撃ってはならない側: 「未実装」と書いてあれば通す
    marked = {"G-98": " 何か | 閾値。**未実装**(L9 で実装する) |"}
    assert not [
        gid for gid, rest in marked.items() if gid not in refs and UNIMPLEMENTED not in rest
    ]
