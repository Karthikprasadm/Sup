from sup.cli import run_source


def test_define_and_call_function():
    code = (
        """
sup
  define function called area with width and height
    set result to multiply width and height
    return result
  end function

  set w to 3
  set h to 4
  print call area with w and h
bye
""".strip()
    )
    out = run_source(code)
    assert out.splitlines() == ["12.0"]


def test_transpile_python():
    code = (
        """
sup
  define function called add2 with a and b
    return add a and b
  end function
  print call add2 with 2 and 3
bye
""".strip()
    )
    py = run_source(code, emit="python")
    assert "def add2(a, b):" in py
    assert "def __main__():" in py

