Sup Language
============

Sup is an English-like programming language with deterministic semantics and human-friendly errors!!!

- Variables, arithmetic, strings
- Collections (lists, maps)
- Control flow (if/else, while, for each)
- Functions
- Errors and imports
- Transpiler to Python

Get started:
```
sup sup-lang/examples/06_mixed.sup
```

Safe mode & capabilities
------------------------

By default, the interpreter blocks potentially dangerous operations. Enable what you need via `SUP_CAPS` (comma-separated), or disable gating with `SUP_UNSAFE=1`.

- Capabilities: `net`, `process`, `fs_write`, `archive`, `sql`

Example (PowerShell):
```
$env:SUP_CAPS = "fs_write,net"
```

Dev workflow
------------

```
pip install -e ./sup-lang pytest ruff mypy
ruff check sup-lang/sup --fix
mypy --config-file sup-lang/mypy.ini sup-lang/sup
pytest -q sup-lang
```

Distribution (v2.8.0)
---------------------

- PyPI: `sup-lang` — `pip install sup-lang`
- VS Code Marketplace: `wingspawn.sup-lang-support`
- Open VSX: `Karthikprasadm.sup-lang-support`

Links: [Marketplace](https://marketplace.visualstudio.com/items?itemName=wingspawn.sup-lang-support) · [Open VSX](https://open-vsx.org/extension/Karthikprasadm/sup-lang-support)

CI/Perf
-------

The CI perf job runs a self-contained inline benchmark using `sup.cli.run_source`, produces `perf.json` at the repository root, and enforces a simple budget gate.


See also
--------

- Language specification (v1.0): `spec.md`
- Versioning and stability policy: `versioning.md`

