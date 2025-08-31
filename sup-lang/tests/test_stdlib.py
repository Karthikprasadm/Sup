from sup.cli import run_source


def test_stdlib_math_and_strings():
    code = """
sup
set word to "hello"
print upper of word
print length of word
print power of 2 and 5
print absolute of -42
bye
""".strip()
    out = run_source(code)
    assert out.splitlines() == [
        "HELLO",
        "5",
        "32.0",
        "42.0",
    ]


def test_env_and_path_and_regex_and_args(monkeypatch):
    monkeypatch.setenv("SUP_ARGS", "foo bar")
    code = """
sup
set home to env get of "HOME"
print basename of "/tmp/file.txt"
print dirname of "/tmp/file.txt"
print join path of "/tmp" and "x"
print exists of "."
print regex match of "^f.*" and "foo"
print regex search of "bar" and "foo bar baz"
print regex replace of "bar" and "foo bar baz" and "qux"
print args get
print args get of 1
bye
""".strip()
    out = run_source(code)
    lines = out.splitlines()
    assert lines[0] == "file.txt"
    assert lines[1] in {"/tmp", "\\tmp"}
    assert lines[2].endswith("x")
    assert lines[3] in {"True", "False"}
    assert lines[4] == "True"
    assert lines[5] == "True"
    assert lines[6] == "foo qux baz"
    assert lines[7] == "foo bar"
    assert lines[8] == "bar"


def test_subprocess_glob_random_crypto_datetime(tmp_path, monkeypatch):
    # create some files for glob
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("hello", encoding="utf-8")
    f2.write_text("world", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    code = """
sup
print glob of "*.txt"
set xs to make list of 1, 2, 3
print shuffle of xs
print choice of xs
print hash sha256 of "abc"
print time now
print format date of 0 and "%Y"
print spawn of "echo sup"
bye
""".strip()
    out = run_source(code)
    lines = out.splitlines()
    # glob returns a Python list repr; ensure both files are present
    glob_line = lines[0]
    assert "a.txt" in glob_line and "b.txt" in glob_line
    # shuffled list prints repr of list
    assert lines[1].startswith("[") and lines[1].endswith("]")
    # choice yields one element of xs
    assert lines[2] in {"1", "2", "3"}
    # sha256 of abc
    assert (
        lines[3] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    # time now is a float string
    float(lines[4])
    # epoch 0 formatted year is 1970
    assert lines[5] == "1970"
    # spawn echo
    assert "sup" in lines[6].strip().lower()
