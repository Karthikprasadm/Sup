from sup.cli import run_source


def test_if_and_repeat():
    code = (
        """
sup
  set a to 5
  set b to 3
  if a is greater than b then
    print a
  end if
  repeat 3 times
    print multiply a and b
  end repeat
bye
""".strip()
    )
    out = run_source(code)
    assert out.splitlines() == ["5", "15", "15", "15"]

