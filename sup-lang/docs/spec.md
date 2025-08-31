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

Standard Library (selected)
---------------------------
- Strings/Math: `upper of S`, `lower of S`, `trim of S`, `concat of A and B`, `power of A and B`, `sqrt of A`, `abs of A`, `min of A and B`, `max of A and B`, `floor of A`, `ceil of A`, `contains of A and B`, `join of SEPARATOR and LIST`
- Files/JSON/Time: `read file of PATH`, `write file of PATH and DATA`, `json parse of S`, `json stringify of V`, `now`
- Env/Path:
  - `env get of KEY` -> returns value or null
  - `env set of KEY and VALUE` -> returns true
  - `cwd` -> current working directory
  - `join path of A and B` -> OS-specific path join
  - `basename of PATH`, `dirname of PATH`, `exists of PATH`
- Logging: `log of MESSAGE` (writes to output stream)
- Regex: `regex match of PATTERN and TEXT`, `regex search of PATTERN and TEXT`, `regex replace of PATTERN and TEXT and REPLACEMENT`
- Args (CLI): `args get` -> all args joined by spaces; `args get of INDEX` -> positional arg by index (0-based), or null if missing. CLI passes all trailing tokens after file to program via `SUP_ARGS`.

Additional Modules
------------------
- HTTP: `http get of URL`, `http post of URL and BODY` (returns response text)
- Subprocess: `spawn of CMD` (returns stdout text, raises on nonzero)
- Globbing: `glob of PATTERN` (returns list of matched paths)
- Random: `random int of A and B`, `random float`, `shuffle of LIST`, `choice of LIST`
- Crypto: `hash md5 of S`, `hash sha1 of S`, `hash sha256 of S`
- Datetime: `time now` (seconds since epoch), `format date of TS and "%Y-%m-%d"`

Design goals (FAQ)
------------------
- Readable: strict grammar that reads like English
- Deterministic: no magical state; explicit evaluation order
- Helpful errors: line numbers and suggestions when possible
- Progressive: interpreter first, transpiler available for ecosystem integration

Performance & Tooling
---------------------
- Optimizer: `--opt` enables constant folding and simple AST rewrites during run/transpile
- Transpiler sourcemaps: `--emit python --sourcemap` appends inline source mapping comments per line
- Benchmarks: `python -m sup.tools.benchmarks` prints CSV for basic scenarios; set perf budgets in CI as needed
- Future backends: experimental VM/JIT/WASM not enabled by default; CLI may expose `--backend vm` later

Grammar (EBNF)
--------------
The following is an informal EBNF for SUP v0.2:

```
program      = ws* "sup" nl statements ws* "bye" ws* ;
statements   = { statement nl } ;
statement    = assignment | print | if | while | repeat | foreach | funcdef | return | callstmt | trycatch | throw | exprstmt ;
assignment   = "set" ( ident | "result" | string ) "to" expression [ "in" value ] ;
print        = "print" ( "the" ("result" | ident | "list" | "map") | "result" | expression ) ;
if           = "if" boolexpr ["then"] nl statements ["else" nl statements] "end if" ;
while        = "while" boolexpr nl statements "end while" ;
repeat       = "repeat" value "times" nl statements "end repeat" ;
foreach      = "for each" ident "in" value nl statements "end for" ;
funcdef      = "define function called" ident ["with" ident {"and" ident}] nl statements "end function" ;
return       = "return" [ expression ] ;
callstmt     = "call" ident ["with" expression {"and" expression}] ;
trycatch     = "try" nl statements ["catch" [ident] nl statements] ["finally" nl statements] "end try" ;
throw        = "throw" expression ;
exprstmt     = expression ;

boolexpr     = boolterm {"or" boolterm} ;
boolterm     = boolfactor {"and" boolfactor} ;
boolfactor   = ["not"] ( compare | value ) ;
compare      = value relop value ;
relop        = ">" | "<" | "==" | "!=" | ">=" | "<=" ;

expression   = add | sub | mul | div | call | make | builtin | value ;
add          = "add" value "and" value ;
sub          = "subtract" ( value "and" value | value "from" value ) ;
mul          = "multiply" value "and" value ;
div          = "divide" value "by" value ;
make         = "make" ( list | map ) ;
list         = "list" "of" value {"," value} ;
map          = "map" ;
builtin      = builtin_op ;  // see stdlib for forms
call         = "call" ident ["with" expression {"and" expression}] ;
value        = number | string | ident | "result" | make | call | add | sub | mul | div ;

ident        = /[A-Za-z_][A-Za-z0-9_]*/ ;
number       = /-?\d+(\.\d+)?/ ;
string       = '"' ( '\\' any | not('"') )* '"' ;
nl           = /\r?\n/ ;
ws           = /[ \t]*/ ;
```

Semantics
---------
- Evaluation order: left‑to‑right, expressions strictly evaluated; no short‑circuit for arithmetic; boolean `and`/`or` short‑circuit.
- Variables are case‑insensitive identifiers in the current scope; assignment updates `last_result`.
- Control flow: `repeat N times` executes body N times (N coerced to int), `while` evaluates condition each loop.
- Functions: lexical scoping, arguments bound by name position; `return` exits current function with optional value.
- Errors: runtime errors raise and can be handled by `try`/`catch`/`finally`; `throw` raises arbitrary values.
- Modules/imports: `import foo` binds module namespace `foo.*`; `from foo import bar as baz` binds symbol directly. Resolution searches CWD then `SUP_PATH`.
- Concurrency: not yet specified (single‑threaded). Future versions may add `spawn task`, message passing, and async IO.

