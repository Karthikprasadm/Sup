from sup.cli import run_source


def test_if_else_and_comparisons():
    code = (
        """
sup
  set x to 7
  if x is greater than 5
    print "big"
  else
    print "small"
  end if

  if x is less than 0 or x is equal to 7
    print "match"
  end if
bye
""".strip()
    )
    out = run_source(code)
    assert out.splitlines() == ["big", "match"]

