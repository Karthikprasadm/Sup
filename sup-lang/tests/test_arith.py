from sup.cli import run_source


def run(code: str) -> str:
    return run_source(code)


def test_add_sub_mul_div():
    out = run(
        """
sup
  print add 2 and 3
  print subtract 45 and 35
  set total to multiply 4 and 5
  print divide total by 4
bye
""".strip()
    )
    assert out.splitlines() == ["5", "10", "5.0"]

