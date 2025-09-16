from __future__ import annotations

import argparse
import os
import re
import sys

from . import __version__
from .errors import SupError
from .interpreter import Interpreter

try:
    from .optimizer import optimize_ex
except Exception:  # pragma: no cover - fallback for environments missing optimizer

    def optimize_ex(program, *, enabled_passes=None, collect_timings=False, dump_stream=None):  # type: ignore[override]
        return program, {}


from .parser import AST  # type: ignore
from .parser import Parser
from .transpiler import build_sourcemap_mappings, to_python, to_python_with_map

try:
    from .typecheck import check as tc_check
except Exception:  # pragma: no cover - fallback if typecheck is unavailable

    def tc_check(_program):  # type: ignore[override]
        return []


def run_source(
    source: str, *, stdin: str | None = None, emit: str | None = None
) -> str:
    parser = Parser()
    program = parser.parse(source)
    if emit == "python":
        return to_python(program)
    interpreter = Interpreter()
    return interpreter.run(program, stdin=stdin)


def run_file(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        output = run_source(source)
        if output:
            sys.stdout.write(output)
        return 0
    except SupError as e:
        sys.stderr.write(str(e) + "\n")
        return 2
    except Exception as e:
        # Catch-all to avoid hanging on unexpected exceptions
        sys.stderr.write(str(e) + "\n")
        return 2


def repl() -> int:
    print("sup (type 'bye' to exit)")
    buffer: list[str] = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            print()
            break
        if line.strip().lower() == "bye":
            break
        buffer.append(line)
        if line.strip().lower() == "bye":
            # unreachable due to break above, kept for clarity
            pass
        # Execute when a program block is complete: detect lines starting with 'sup' and ending with 'bye'
        src = "\n".join(buffer)
        if (
            "\n" in src
            and src.strip().lower().startswith("sup")
            and src.strip().lower().endswith("bye")
        ):
            try:
                out = run_source(src)
                if out:
                    print(out, end="")
            except SupError as e:
                print(str(e))
            except Exception as e:
                print(str(e))
            buffer.clear()
    return 0


def _resolve_module_path(module: str) -> str:
    # Search SUP_PATH then CWD for module.sup
    search_paths: list[str] = []
    env_path = os.environ.get("SUP_PATH")
    if env_path:
        search_paths.extend(env_path.split(os.pathsep))
    search_paths.append(os.getcwd())
    for base in search_paths:
        candidate = os.path.join(base, f"{module}.sup")
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"Cannot find module '{module}' (searched {search_paths})")


def _gather_imports(program: AST.Program, acc: set[str]) -> None:
    def walk(node: AST.Node) -> None:  # type: ignore[override]
        if isinstance(node, AST.Import):
            acc.add(node.module)
        elif isinstance(node, AST.FromImport):
            acc.add(node.module)
        # Recurse into composite nodes
        for attr in (
            "statements",
            "body",
            "else_body",
            "count_expr",
            "expr",
            "left",
            "right",
            "iterable",
        ):
            if hasattr(node, attr):
                val = getattr(node, attr)
                if isinstance(val, list):
                    for x in val:
                        if isinstance(x, AST.Node):
                            walk(x)
                elif isinstance(val, AST.Node):
                    walk(val)
        # Also check common fields that are lists of nodes
        if isinstance(node, AST.Program):
            for s in node.statements:
                walk(s)

    walk(program)  # type: ignore[arg-type]


def transpile_project(entry_file: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    parser = Parser()

    visited: set[str] = set()

    entry_module: str | None = None
    entry_module_py: str | None = None

    def sanitize_module(name: str) -> str:
        safe = re.sub(r"[^0-9A-Za-z_]", "_", name)
        if not re.match(r"[A-Za-z_]", safe):
            safe = "m_" + safe
        return safe

    def transpile_file(path: str) -> None:
        src = open(path, encoding="utf-8").read()
        program = parser.parse(src)
        # Write .py next to out_dir with module name
        module_name = os.path.splitext(os.path.basename(path))[0]
        py_module = sanitize_module(module_name)
        py_path = os.path.join(out_dir, f"{py_module}.py")
        py_code, src_lines, src_cols = to_python_with_map(program)
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(py_code)
        # Write a sourcemap using the per-line source mapping captured by the emitter
        try:
            mappings = build_sourcemap_mappings(src_lines, src_cols)
            sm = {
                "version": 3,
                "file": os.path.basename(py_path),
                "sources": [os.path.basename(path)],
                "names": [],
                "mappings": mappings,
            }
            with open(py_path + ".map", "w", encoding="utf-8") as mf:
                import json as _json

                mf.write(_json.dumps(sm))
        except Exception:
            # best-effort; ignore mapping failures
            pass
        nonlocal entry_module
        nonlocal entry_module_py
        if entry_module is None:
            entry_module = module_name
            entry_module_py = py_module
        # Recurse into imports
        imports: set[str] = set()
        _gather_imports(program, imports)
        for mod in imports:
            if mod not in visited:
                visited.add(mod)
                mod_path = _resolve_module_path(mod)
                transpile_file(mod_path)

    visited.add(os.path.splitext(os.path.basename(entry_file))[0])
    transpile_file(entry_file)
    # Write a simple runner that calls entry_module.__main__()
    if entry_module_py:
        run_path = os.path.join(out_dir, "run.py")
        with open(run_path, "w", encoding="utf-8") as rf:
            rf.write(
                f"from {entry_module_py} import __main__ as _m\n\nif __name__ == '__main__':\n    _m()\n"
            )


def main(argv: list[str] | None = None) -> int:
    # Make CLI robust: treat 'transpile' as a dedicated mode; otherwise accept 'file' and '--emit'.
    if argv is None:
        argv = sys.argv[1:]

    # Route explicitly to transpile mode if first token is 'transpile'
    if len(argv) > 0 and argv[0] == "transpile":
        p_tr = argparse.ArgumentParser(
            prog="sup transpile",
            description="Transpile a sup program (and its imports) to Python files",
        )
        p_tr.add_argument("entry", help="Entry .sup file")
        p_tr.add_argument("--out", required=True, help="Output directory for .py files")
        tr_args = p_tr.parse_args(argv[1:])
        try:
            transpile_project(tr_args.entry, tr_args.out)
            print(f"Transpiled to {tr_args.out}")
            return 0
        except Exception as e:
            sys.stderr.write(str(e) + "\n")
            return 2

    # Package/typecheck subcommands: build, lock, test, publish, check, init, install
    if len(argv) > 0 and argv[0] in {
        "build",
        "lock",
        "test",
        "publish",
        "check",
        "init",
        "install",
    }:
        cmd = argv[0]
        if cmd == "install":
            p = argparse.ArgumentParser(
                prog="sup install",
                description="Install a SUP module from a local directory or HTTP registry",
            )
            p.add_argument(
                "name", help="Module name to install (optionally name@version)"
            )
            p.add_argument(
                "--registry",
                default=os.path.join(os.getcwd(), "registry"),
                help="Path to local registry or HTTP base URL (default: ./registry)",
            )
            args_i2 = p.parse_args(argv[1:])
            try:
                name_ver = args_i2.name
                if "@" in name_ver:
                    name, ver = name_ver.split("@", 1)
                else:
                    name, ver = name_ver, None
                # local dir registry
                if args_i2.registry.startswith(
                    "http://"
                ) or args_i2.registry.startswith("https://"):
                    import json as _json
                    import urllib.request as _u

                    meta_url = (
                        args_i2.registry.rstrip("/")
                        + f"/resolve?name={name}&version={ver or '*'}"
                    )
                    with _u.urlopen(meta_url) as r:
                        if r.getcode() // 100 != 2:
                            raise RuntimeError("Registry resolve failed")
                        meta = _json.loads(r.read().decode("utf-8"))
                    src_code = meta.get("source", "")
                    if not src_code:
                        raise RuntimeError("Registry returned empty source")
                else:
                    reg_dir = os.path.abspath(args_i2.registry)
                    cand = os.path.join(reg_dir, f"{name}.sup")
                    if not os.path.exists(cand):
                        raise FileNotFoundError(
                            f"Module '{name}' not found in {reg_dir}"
                        )
                    src_code = open(cand, encoding="utf-8").read()
                # Write to project
                dst = os.path.join(os.getcwd(), f"{name}.sup")
                with open(dst, "w", encoding="utf-8") as wf:
                    wf.write(src_code)
                # Update lockfile v2 (JSON)
                import hashlib as _hh
                import json as _json

                h = _hh.sha256(src_code.encode("utf-8")).hexdigest()
                lock_path = os.path.join(os.getcwd(), "sup.lock.json")
                lock: dict = {"version": 2, "modules": {}}
                if os.path.exists(lock_path):
                    try:
                        lock = _json.loads(open(lock_path, encoding="utf-8").read())
                    except Exception:
                        pass
                lock.setdefault("modules", {})[name] = {
                    "sha256": h,
                    "source": "url" if args_i2.registry.startswith("http") else "local",
                    "version": ver or "*",
                }
                with open(lock_path, "w", encoding="utf-8") as lf:
                    lf.write(_json.dumps(lock, indent=2))
                print(f"Installed {name} -> {dst}")
                return 0
            except Exception as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        if cmd == "check":
            p = argparse.ArgumentParser(
                prog="sup check", description="Static checks for a SUP file"
            )
            p.add_argument("file", help=".sup file to check")
            args_c = p.parse_args(argv[1:])
            try:
                src = open(args_c.file, encoding="utf-8").read()
                program = Parser().parse(src)
                errs = tc_check(program)
                for e in errs:
                    loc = f"{args_c.file}:{e.line}" if e.line else args_c.file
                    print(f"{loc}: {e.code}: {e.message}")
                return 1 if errs else 0
            except Exception as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        if cmd == "build":
            p = argparse.ArgumentParser(
                prog="sup build", description="Build a SUP project"
            )
            p.add_argument("entry", help="Entry .sup file")
            p.add_argument(
                "--out", required=True, help="Output directory for build artifacts"
            )
            args_b = p.parse_args(argv[1:])
            try:
                transpile_project(args_b.entry, args_b.out)
                print(f"Built to {args_b.out}")
                return 0
            except Exception as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        if cmd == "lock":
            p = argparse.ArgumentParser(
                prog="sup lock", description="Create a lockfile for a SUP project"
            )
            p.add_argument("entry", help="Entry .sup file")
            args_l = p.parse_args(argv[1:])
            try:
                import hashlib as _hh
                import json as _json

                parser = Parser()
                src = open(args_l.entry, encoding="utf-8").read()
                program = parser.parse(src)
                mods: set[str] = set()
                _gather_imports(program, mods)

                modules: dict[str, dict] = {}
                entry_name = os.path.splitext(os.path.basename(args_l.entry))[0]
                all_modules = set(mods)
                all_modules.add(entry_name)
                for mod in sorted(all_modules):
                    if mod == entry_name:
                        path = os.path.abspath(args_l.entry)
                    else:
                        path = _resolve_module_path(mod)
                    code = open(path, "rb").read()
                    sha256 = _hh.sha256(code).hexdigest()
                    modules[mod] = {
                        "version": "*",
                        "sha256": sha256,
                        "path": os.path.relpath(path, os.getcwd()),
                        "source": "local",
                    }
                lock_obj = {"version": 2, "modules": modules}
                lock_path_json = os.path.join(os.getcwd(), "sup.lock.json")
                with open(lock_path_json, "w", encoding="utf-8") as lf:
                    lf.write(_json.dumps(lock_obj, indent=2))
                print(f"Wrote lockfile {lock_path_json}")
                return 0
            except Exception as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        if cmd == "test":
            p = argparse.ArgumentParser(
                prog="sup test", description="Run .sup tests in a directory"
            )
            p.add_argument("tests_dir", help="Directory containing .sup test files")
            args_t = p.parse_args(argv[1:])
            try:
                any_failed = False
                for root, _dirs, files in os.walk(args_t.tests_dir):
                    for fn in files:
                        if fn.lower().endswith(".sup"):
                            path = os.path.join(root, fn)
                            rc = run_file(path)
                            if rc != 0:
                                any_failed = True
                return 1 if any_failed else 0
            except Exception as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        if cmd == "publish":
            p = argparse.ArgumentParser(
                prog="sup publish",
                description="Create a distributable tarball of a SUP project or upload to a registry",
            )
            p.add_argument("project_dir", help="Project directory containing sup.json")
            p.add_argument(
                "--registry", help="HTTP registry base URL (if provided, upload)"
            )
            args_p = p.parse_args(argv[1:])
            try:
                import hashlib as _hh
                import json
                import tarfile
                import urllib.request as _u

                proj = os.path.abspath(args_p.project_dir)
                meta_path = os.path.join(proj, "sup.json")
                data = json.loads(open(meta_path, encoding="utf-8").read())
                name = data.get("name", "app")
                version = data.get("version", "0.0.0")
                entry = data.get("entry", "main.sup")
                out_dir = os.path.join(proj, "dist_sup")
                os.makedirs(out_dir, exist_ok=True)
                tar_name = f"{name}-{version}.tar.gz"
                tar_path = os.path.join(out_dir, tar_name)
                with tarfile.open(tar_path, "w:gz") as tf:
                    # include entry and metadata for now
                    tf.add(os.path.join(proj, entry), arcname=entry)
                    tf.add(meta_path, arcname="sup.json")
                # integrity
                digest = _hh.sha256(open(tar_path, "rb").read()).hexdigest()
                if args_p.registry:
                    # POST to registry: /upload?name=&version=&sha256=
                    url = args_p.registry.rstrip("/") + "/upload"
                    body = json.dumps(
                        {"name": name, "version": version, "sha256": digest}
                    ).encode("utf-8")
                    req = _u.Request(
                        url, data=body, headers={"Content-Type": "application/json"}
                    )
                    with _u.urlopen(req) as r:
                        if r.getcode() // 100 != 2:
                            raise RuntimeError("Registry upload failed")
                print(f"Created {tar_path}")
                return 0
            except Exception as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        if cmd == "init":
            p = argparse.ArgumentParser(
                prog="sup init", description="Scaffold a new SUP project"
            )
            p.add_argument("name", help="Project name")
            p.add_argument("--dir", default=".", help="Target directory (default: .)")
            args_i = p.parse_args(argv[1:])
            try:
                proj = os.path.abspath(args_i.dir)
                os.makedirs(proj, exist_ok=True)
                main_path = os.path.join(proj, "main.sup")
                json_path = os.path.join(proj, "sup.json")
                if not os.path.exists(main_path):
                    with open(main_path, "w", encoding="utf-8") as f:
                        f.write(
                            """sup
print "Hello from SUP!"
bye
"""
                        )
                meta = {
                    "name": args_i.name,
                    "version": "0.1.0",
                    "entry": "main.sup",
                }
                import json as _json

                with open(json_path, "w", encoding="utf-8") as jf:
                    jf.write(_json.dumps(meta, indent=2))
                print(f"Initialized project '{args_i.name}' in {proj}")
                return 0
            except Exception as e:
                sys.stderr.write(str(e) + "\n")
                return 2

    # Default mode: run a file or start a REPL; optional --emit python; --version
    arg_parser = argparse.ArgumentParser(prog="sup", description="Sup language CLI")
    arg_parser.add_argument("file", nargs="?", help="Path to .sup file to run")
    arg_parser.add_argument(
        "--emit",
        choices=["python"],
        help="Transpile to target language and print",
    )
    arg_parser.add_argument(
        "--opt", action="store_true", help="Run optimizer on AST before execution"
    )
    arg_parser.add_argument(
        "--version", action="store_true", help="Print version and exit"
    )
    arg_parser.add_argument(
        "--opt-passes",
        help=(
            "Comma-separated passes to run: const_fold,dead_branch,copy_prop,cse,inline,dce_pure,jump_thread"
        ),
    )
    arg_parser.add_argument(
        "--opt-dump",
        help="Path to write optimized AST (use '-' for stdout)",
    )
    arg_parser.add_argument(
        "--opt-timings",
        action="store_true",
        help="Print per-pass timings (ms)",
    )
    args = arg_parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.file:
        if args.emit:
            with open(args.file, encoding="utf-8") as f:
                src = f.read()
            try:
                if args.emit == "python":
                    program = Parser().parse(src)
                    py_code, src_lines, _src_cols = to_python_with_map(program)
                    sys.stdout.write(py_code)
                    return 0
                out = run_source(src, emit=args.emit)
                if out:
                    sys.stdout.write(out)
                return 0
            except SupError as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        # normal execute path; apply optimizer if requested
        try:
            with open(args.file, encoding="utf-8") as f:
                src = f.read()
            parser2 = Parser()
            program = parser2.parse(src)
            if args.opt:
                passes = None
                if args.opt_passes:
                    passes = [
                        p.strip() for p in args.opt_passes.split(",") if p.strip()
                    ]
                dump_file = None
                dump_stream = None
                if args.opt_dump:
                    dump_file = args.opt_dump
                    if dump_file == "-":
                        dump_stream = sys.stdout
                    else:
                        try:
                            dump_stream = open(dump_file, "w", encoding="utf-8")
                        except Exception:
                            dump_stream = None
                program, timings = optimize_ex(
                    program,
                    enabled_passes=passes,
                    collect_timings=args.opt_timings,
                    dump_stream=dump_stream,
                )
                if dump_stream is not None and dump_stream is not sys.stdout:
                    try:
                        dump_stream.close()  # type: ignore[call-arg]
                    except Exception:
                        pass
                if args.opt_timings and timings:
                    for k in sorted(timings.keys()):
                        print(f"opt[{k}]: {timings[k]:.3f} ms", file=sys.stderr)
            interp = Interpreter()
            out = interp.run(program)
            if out:
                sys.stdout.write(out)
            return 0
        except SupError as e:
            sys.stderr.write(str(e) + "\n")
            return 2
        except Exception as e:
            sys.stderr.write(str(e) + "\n")
            return 2
    return repl()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
