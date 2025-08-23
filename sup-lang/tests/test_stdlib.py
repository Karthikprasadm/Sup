from sup.cli import run_source


def test_stdlib_math_and_strings():
    code = (
        """
sup
set word to "hello"
print upper of word
print length of word
print power of 2 and 5
print absolute of -42
bye
""".strip()
    )
    out = run_source(code)
    assert out.splitlines() == [
        "HELLO",
        "5",
        "32.0",
        "42.0",
    ]

