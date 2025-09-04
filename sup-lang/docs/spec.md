Language Specification
======================

Grammar highlights:
- Program starts with `sup` and ends with `bye`.
- Assignments: `set x to add 2 and 3`
- Print: `print the result` or `print <expr>`
- Input: `ask for name`
- If/Else: `if a is greater than b then ... else ... end if`
- While: `while cond ... end while`
- For Each: `for each item in list ... end for`
- Errors: `try ... catch e ... finally ... end try`, `throw <expr>`
- Imports: `import foo`, `from foo import bar as baz`

Booleans and comparisons: `and`, `or`, `not`, `==`, `!=`, `<`, `>`, `<=`, `>=`.

Design goals (FAQ)
------------------
- Readable: strict grammar that reads like English
- Deterministic: no magical state; explicit evaluation order
- Helpful errors: line numbers and suggestions when possible
- Progressive: interpreter first, transpiler available for ecosystem integration

Semantics
---------

Truthiness:
- Falsey: `0`, `0.0`, empty string `""`, empty list `[]`, empty map `{}`, and `False`.
- Everything else is truthy. `not` applies Python-like truthiness.

Operator table (left to right, no precedence mixing beyond what grammar allows):

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

