Changelog
=========

All notable changes to this project will be documented here.

0.2.2 – 2025-08-24
-------------------
Added
- Release automation (PyPI + VSIX) via GitHub Actions
- Docs workflow and MkDocs site scaffolding
- Python transpiler project mode (sup transpile …) with sanitized module names and run.py
- Stdlib: min, max, floor, ceil, trim, contains, join, now, read file, write file, json parse, json stringify
- List index access (get N from list)

Fixed
- Transpiled last_result handling and global scoping in functions
- Circular import detection in interpreter

0.2.0 – 2025-08-24
-------------------
Initial MVP
- Parser, AST, interpreter, CLI
- Arithmetic, variables, printing, input
- Conditionals/loops, functions
- Collections (lists/maps), errors/imports
- Python transpiler (single file)
- Examples and test suite


