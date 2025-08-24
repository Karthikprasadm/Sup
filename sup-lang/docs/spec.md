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

