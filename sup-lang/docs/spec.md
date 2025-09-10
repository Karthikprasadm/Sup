Language Specification (v1.0)
=============================

Grammar
-------
- Program starts with `sup` and ends with `bye`.
- Assignments: `set x to add 2 and 3`
- Print: `print the result` or `print <expr>`
- Input: `ask for name`
- If/Else: `if a is greater than b then ... else ... end if`
- While: `while cond ... end while`
- For Each: `for each item in list ... end for`
- Errors: `try ... catch e ... finally ... end try`, `throw <expr>`
- Imports: `import foo`, `from foo import bar as baz`

Collections
-----------
- `make list [of A{, B}*]`, `make map`
- `push X to list`, `pop from list`
- `get K from map|list`, `set K to V in map`, `delete K from map`, `length of <expr>`

Booleans and comparisons: `and`, `or`, `not`, `==`, `!=`, `<`, `>`, `<=`, `>=`.

Design goals (FAQ)
------------------
- Readable: strict grammar that reads like English
- Deterministic: no magical state; explicit evaluation order
- Helpful errors: line numbers and suggestions when possible
- Progressive: interpreter first, transpiler available for ecosystem integration

Semantics (deterministic)
------------------------

Truthiness:
- Falsey: `0`, `0.0`, empty string `""`, empty list `[]`, empty map `{}`, and `False`.
- Everything else is truthy. `not` applies Python-like truthiness.

Operator table (left to right; grammar restricts precedence):

- Arithmetic: `+`, `-`, `*`, `/` (numeric operands; division yields float)
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=` (numeric compares for numbers, structural equality for lists/maps)
- Boolean: `and`, `or`, `not` (short-circuit behavior is preserved by evaluation order)

Strings vs bytes:
- Strings are Unicode text (UTF-8 encoded in files). There is no separate bytes type in the MVP.
- File IO reads/writes strings. Future versions may add explicit bytes and encoding options.

Unicode handling:
- Source files must be UTF-8. A UTF-8 BOM is tolerated and stripped.
- Identifiers are ASCII in MVP; string literals support full Unicode.

Scoping and shadowing:
- Variables are lexical within a function body; assignment updates the nearest scope.
- Function parameters shadow outer variables of the same name.
- Module imports bind names at the top level; `import m as mm` creates a module namespace `mm`.
- `from m import f as g` binds `g` directly in the current scope.

Modules and imports
-------------------
- Search path: `SUP_PATH` (pathsep-separated) then current working directory.
- Circular imports raise a diagnostic naming the module.
- `import m` loads `m.sup` into an isolated environment and exposes a namespace.
- `from m import f as g` binds definitions from that namespace.

Error model
-----------
- Runtime errors include a message and (when available) a line number.
- `throw <expr>` raises an error carrying the evaluated value.
- `try/catch/finally`: `catch name` binds the thrown value; `finally` always runs and rethrows if not caught.

Determinism and numerics
------------------------
- `/` yields floating‑point division; `+`, `-`, `*` are numeric with integer folding when exact.
- Comparisons on numbers are numeric; lists/maps use structural equality.
- Truthiness: falsey values are `0`, `0.0`, `""`, `[]`, `{}`, and `False`; everything else is truthy.

Capability model (runtime)
--------------------------
- Default safe mode denies: network, subprocess, filesystem writes, archiving, sqlite.
- Enable capabilities via `SUP_CAPS=net,process,fs_write,archive,sql` or disable all gates with `SUP_UNSAFE=1`.
- Stdlib functions requiring capabilities fail with a clear message when not enabled.

Resource limits (sandbox)
-------------------------
- Limits are optional and configured via environment variables:
  - `SUP_LIMIT_WALL_MS`: maximum wall-clock time for a single run in milliseconds.
  - `SUP_LIMIT_STEPS`: maximum AST evaluation steps.
  - `SUP_LIMIT_MEM_MB`: soft memory cap (bytes tracked via tracemalloc).
  - `SUP_LIMIT_FD`: maximum concurrently open files/handles counted by the interpreter.
- Exceeding a limit aborts execution with an error of the form `Resource limit exceeded: <kind>`.

Deterministic mode
------------------
- `SUP_DETERMINISTIC=1` enables reproducible behavior; `SUP_SEED` provides a numeric seed.
- Current effects:
  - `random_bytes(n)`: generated from the seeded PRNG.
  - `now`: returns `1970-01-01T00:00:00`.
- Additional APIs may opt into deterministic behavior in future minor releases; such changes are additive.

