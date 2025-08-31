Standard Library
================

Math
----
- `power of A and B` – exponentiation
- `min of A and B`, `max of A and B`
- `sqrt of X`, `floor of X`, `ceil of X`, `absolute of X`

Examples:
```
sup
  print power of 2 and 10
  print min of 4 and 9
  print floor of 3.7
bye
```

Strings
-------
- `upper of S`, `lower of S`, `trim of S`, `length of S`, `concat of A and B`
- `join of SEP and LIST`

Examples:
```
sup
  set name to "Sup"
  print upper of name
  print concat of name and "!"
  print join of ", " and make list of "a", "b", "c"
bye
```

Collections
-----------
- `make list of ...`, `push`, `pop`, `length of L`
- `make map`, `set "k" to v in map`, `get "k" from map`, `delete "k" from map`
- `get N from list`

Examples:
```
sup
  make list of 1, 2, 3
  push 4 to list
  print get 0 from list
  make map
  set "name" to "Ada" in map
  print get "name" from map
bye
```

I/O and JSON
------------
- `read file of PATH`, `write file of PATH and DATA`
- `json parse of STRING`, `json stringify of VALUE`
- `now` – current timestamp (ISO)

Environment, Paths, and Regex
------------------------------
- `env get of KEY`, `env set of KEY and VALUE`
- `cwd`, `join path of A and B`, `basename of PATH`, `dirname of PATH`, `exists of PATH`
- `regex match/search/replace`

CLI Args
--------
- `args get` – all args joined by spaces
- `args get of INDEX` – positional arg (0‑based) or null

