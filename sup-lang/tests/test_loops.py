from sup.cli import run_source


def test_while_and_foreach():
    code = (
        """
sup
  set x to 0
  while x is less than 3
    print x
    set x to add x and 1
  end while

  make list of 1, 2, 3
  for each item in list
    print item
  end for
bye
""".strip()
    )
    out = run_source(code)
    assert out.splitlines() == ["0", "1", "2", "1", "2", "3"]

