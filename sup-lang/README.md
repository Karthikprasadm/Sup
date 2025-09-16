## SUP — English-like Programming Language

An English-like programming language focused on readability with deterministic semantics.

[![CI](https://github.com/Karthikprasadm/Sup/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthikprasadm/Sup/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://karthikprasadm.github.io/Sup)
[![PyPI](https://img.shields.io/pypi/v/sup-lang.svg)](https://pypi.org/project/sup-lang/)
[![Coverage](https://img.shields.io/codecov/c/github/Karthikprasadm/Sup)](https://codecov.io/gh/Karthikprasadm/Sup)
[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue)](https://marketplace.visualstudio.com/items?itemName=wingspawn.sup-language-support)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

![SUP Demo](assets/demo.gif)

### Quickstart

1. Create a virtual environment and install:
```
python -m venv .venv
.venv\\Scripts\\activate
pip install -e ./sup-lang
```

2. Run a program:
```
sup sup-lang/examples/06_mixed.sup
```

### CLI usage

Run a file:
```
sup path/to/program.sup
```
Emit Python for a single source:
```
sup --emit python path/to/program.sup
```
Transpile entry + imports to a folder and run:
```
sup transpile path/to/entry.sup --out dist_py
python dist_py/run.py
```
Choose backend, enable optimizer and sourcemaps, or launch debugger:
```
sup path/to/program.sup --backend vm
sup path/to/program.sup --opt
sup transpile path/to/entry.sup --out dist_py --sourcemap
sup path/to/program.sup --debug
```
Check version:
```
sup --version
```

3. Dev workflow (lint, types, tests):
```
pip install pytest ruff mypy
ruff check sup-lang/sup --fix
mypy --config-file sup-lang/mypy.ini sup-lang/sup
pytest -q sup-lang
```

Pre-commit hooks (format, lint, import sort, types):
```
pip install pre-commit
pre-commit install -f --install-hooks
pre-commit run -a
```

Format/lint manually:
```
ruff check sup-lang/sup --fix
black sup-lang
isort sup-lang
mypy --config-file sup-lang/mypy.ini sup-lang/sup
```

Debugger, profiler, coverage:
```
sup sup-lang/examples/06_mixed.sup --debug
python -m sup.tools.profiler sup-lang/examples/06_mixed.sup
python -m sup.tools.coverage sup-lang/examples/06_mixed.sup
```

### Language Tour (MVP)

Program structure:
```
sup
  print add 2 and 3
bye
```

Assignments and expressions:
```
sup
  set x to add 10 and 5
  print the result
  print subtract 3 from x
bye
```

Conditionals and loops:
```
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
```

Input:
```
sup
  ask for name
  print name
bye
```

Comments: lines starting with `note` are ignored.

Errors are reported with line numbers and suggestions.

### Phase 2: Functions, Strings, Transpiler

Functions:
```
sup
  define function called area with width and height
    set result to multiply width and height
    return result
  end function

  print call area with 5 and 6
bye
```

Strings:
```
sup
  set name to "Ada"
  print name
bye
```

Transpiler to Python:
```
sup --emit python examples/07_functions.sup
```

Transpile a project (entry + imports) to Python files:
```
sup transpile examples/12_imports.sup --out dist_py
python dist_py/run.py
```
Notes:
- The transpiler performs a DFS on imports and writes sanitized module names into `dist_py/`.
- `run.py` calls the transpiled entry module's `__main__()` to execute top-level code.

### Phase 3: Collections and Stdlib

Lists and Maps:
```
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
bye
```

Stdlib:
- Math: `power of A and B`, `sqrt of X`, `absolute of X`
- String: `length of S`, `upper of S`, `lower of S`, `concat of A and B`
- List: `push`, `pop`, `length of <list>`

Indexing and access:
```
sup
  make list of 1, 2, 3
  print get 0 from list    # prints first element
  make map
  set "k" to 42 in map
  print get "k" from map
bye
```

### Phase 4: Conditionals, Loops, Booleans

Conditionals with else:
```
sup
  if x is greater than 5
    print "big"
  else
    print "small"
  end if
bye
```

While and For Each:
```
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
```

Booleans:
- Operators: `and`, `or`, `not`
- Comparisons: `is equal to`, `is not equal to`, `is greater than`, `is less than`, `is greater than or equal to`, `is less than or equal to`

### Phase 5: Errors and Imports

Errors:
```
sup
  try
    throw "oops"
  catch e
    print e
  finally
    print "done"
  end try
bye
```

Imports:
```
sup
  import mathlib
  print mathlib.pi
  from mathlib import square as sq
  print call sq with 3
bye
```

Notes:
- Interpreter searches modules in `SUP_PATH` (os.pathsep-separated) then CWD.
- Transpiler emits Python `import`/`from` statements; ensure modules exist as Python when executing transpiled code.

### Additional built-ins

- Math: `min of A and B`, `max of A and B`, `floor of X`, `ceil of X`
- String: `trim of S` (strip whitespace), `upper of S`, `lower of S`, `concat of A and B`
- Contains/join:
  - `contains of L and X` where L is a list (true if X in list)
  - `contains of S and T` where S,T are strings (substring check)
  - `join of SEP and LIST` (e.g., `join of "," and list`)

### Safe mode and capabilities

The interpreter is safe-by-default and gates risky operations behind capabilities:

- net, process, fs_write, archive, sql

Enable specific capabilities via environment variable `SUP_CAPS` (comma-separated), or disable gating with `SUP_UNSAFE=1`.

Examples (PowerShell):
```
$env:SUP_CAPS = "fs_write,net"
sup sup-lang/examples/06_mixed.sup
```

Tests auto-enable required caps via `tests/conftest.py`.

### Sandbox limits and deterministic mode

Resource limits (unset = no limit):
- `SUP_LIMIT_WALL_MS`: Max wall-clock time for one run (e.g., `2000`).
- `SUP_LIMIT_STEPS`: Max AST evaluation steps (e.g., `100000`).
- `SUP_LIMIT_MEM_MB`: Soft memory cap via tracemalloc (e.g., `256`).
- `SUP_LIMIT_FD`: Max simultaneously open files/handles tracked by the interpreter (e.g., `64`).

Deterministic mode:
- `SUP_DETERMINISTIC=1`: Enables reproducible behavior; optional `SUP_SEED` seeds the internal PRNG.
- Effects today: `random_bytes` uses a seeded generator; `now` returns `1970-01-01T00:00:00`. More APIs may be added.

Examples (PowerShell):
```
$env:SUP_LIMIT_WALL_MS = "2000"
$env:SUP_LIMIT_STEPS   = "200000"
$env:SUP_LIMIT_MEM_MB  = "256"
$env:SUP_LIMIT_FD      = "64"
sup .\your.sup

# Deterministic run
$env:SUP_DETERMINISTIC = "1"; $env:SUP_SEED = "42"; sup .\your.sup
```

### Error handling notes

- `throw <expr>` raises a runtime error carrying the raw value of `<expr>`; in `catch e`, the variable `e` receives that raw value.
- `finally` always runs whether the `try` body throws or not; if there is no `catch`, the error is re-raised after `finally`.

### Circular imports

- The interpreter detects circular imports and raises a friendly error identifying the module involved.

### Test runner

- To run tests reliably in terminals that buffer output, use:
```
\.venv\Scripts\python sup-lang\tools\run_tests.py
```

### Further reading

- Specification (v1.0): see `docs/spec.md`
- Versioning and stability policy: see `docs/versioning.md`

