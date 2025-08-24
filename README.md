Sup – an English‑like programming language
=========================================

[PyPI](https://pypi.org/project/sup-lang/) • [Docs (MkDocs)](sup-lang/docs/) • [Examples](sup-lang/examples/)

Sup is a tiny, readable programming language whose code looks like English sentences but keeps deterministic, strict semantics. It ships with a parser, AST, interpreter, CLI, a Python transpiler, examples, tests, and CI.

Features
--------
- Programs start with `sup` and end with `bye`
- Variables and arithmetic in English: `set x to add 2 and 3`
- Print: `print the result` or `print <expression>`
- Input: `ask for name`
- Control flow: `if … else … end if`, `while … end while`, `for each item in list … end for`
- Collections: lists and maps (`make list of …`, `make map`, `get 0 from list`, `get "k" from map`)
- Errors/imports: `try/catch/finally`, `throw`, `import foo`, `from foo import bar`
- Stdlib: math/string/collection ops (`power`, `min/max`, `floor/ceil`, `upper/lower/trim`, `contains`, `join`), I/O (`read file`, `write file`), JSON (`json parse`, `json stringify`), `now`
- Transpile to Python (`sup --emit python`) or transpile a whole project (`sup transpile …`)

Install
-------
```
pip install sup-lang
```

CLI
---
Run a program:
```
sup sup-lang/examples/06_mixed.sup
```

REPL: type a full program (from `sup` to `bye`) and it will execute.

Transpile
---------
- Emit Python to stdout for a single source:
```
sup --emit python sup-lang/examples/06_mixed.sup
```
- Transpile an entry file and all imports to a folder with a runnable entrypoint:
```
sup transpile sup-lang/examples/06_mixed.sup --out dist_py
python dist_py/run.py
```

Docs & Examples
---------------
- Quick tour and grammar live in `sup-lang/docs/` (GitHub Pages via Actions)
- Examples are in `sup-lang/examples/`

Development
-----------
```
python -m venv .venv
.venv\Scripts\activate
pip install -e sup-lang
pip install pytest
pytest -q sup-lang
```

Release
-------
Releases are automated via GitHub Actions (tag `v*` triggers build → PyPI publish and VS Code `.vsix` artifact). Add `PYPI_API_TOKEN` to repository secrets.

License
-------
MIT


