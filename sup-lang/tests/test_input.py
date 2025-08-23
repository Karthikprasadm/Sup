from sup.cli import run_source


def test_input_reads_stdin():
    code = (
        """
sup
  ask for name
  print name
bye
""".strip()
    )
    out = run_source(code, stdin="Alice\n")
    assert out.splitlines() == ["Alice"]

