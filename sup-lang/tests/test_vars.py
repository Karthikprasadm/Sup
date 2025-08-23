from sup.cli import run_source


def test_last_result_and_vars():
    code = (
        """
sup
  set x to add 10 and 5
  print the result
  print subtract 3 from x
bye
""".strip()
    )
    out = run_source(code)
    assert out.splitlines() == ["15", "12"]

