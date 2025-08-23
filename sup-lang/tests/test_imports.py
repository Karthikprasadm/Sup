import os
import tempfile
from sup.cli import run_source


def write(tmp, name, src):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)


def test_basic_import_and_from_import(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("SUP_PATH", tmp)
        write(
            tmp,
            "mathlib.sup",
            """
sup
  set pi to 3.14
  define function called square with x
    return multiply x and x
  end function
bye
""".strip(),
        )
        code = (
            """
sup
  import mathlib
  print mathlib.pi
  print call mathlib.square with 2
  from mathlib import square
  print call square with 5
bye
""".strip()
        )
        out = run_source(code)
        assert out.splitlines() == ["3.14", "4.0", "25.0"]


def test_aliasing_and_missing_symbol(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("SUP_PATH", tmp)
        write(
            tmp,
            "m.sup",
            """
sup
  define function called square with x
    return multiply x and x
  end function
bye
""".strip(),
        )
        code = (
            """
sup
  import m as mm
  print call mm.square with 4
  from m import square as sq
  print call sq with 6
bye
""".strip()
        )
        out = run_source(code)
        assert out.splitlines() == ["16.0", "36.0"]

        code_missing = (
            """
sup
  from m import nope
bye
""".strip()
        )
        try:
            run_source(code_missing)
            assert False, "Expected runtime error"
        except Exception as e:
            assert "no symbol" in str(e).lower()


