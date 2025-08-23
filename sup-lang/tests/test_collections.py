from sup.cli import run_source


def test_lists_and_maps():
    code = (
        """
sup
make list of 1, 2, 3
push 4 to list
print the list
pop from list
print the list

make map
set "name" to "Karthik" in map
set "age" to 21 in map
print get "name" from map
delete "age" from map
print the map
print get 0 from list
bye
""".strip()
    )
    out = run_source(code)
    lines = out.splitlines()
    assert lines[0] == "[1, 2, 3, 4]"
    assert lines[1] == "[1, 2, 3]"
    assert lines[2] == "Karthik"
    assert lines[3] == "{'name': 'Karthik'}"
    assert lines[4] == "1"

