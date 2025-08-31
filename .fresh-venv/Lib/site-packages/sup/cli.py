from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
import tarfile

from . import __version__
from .debugger import Debugger
from .errors import SupError
from .interpreter import Interpreter
from .optimizer import optimize
from .parser import AST  # type: ignore
from .parser import Parser
from .sourcemap import remap_exception
from .transpiler import build_sourcemap_json, to_python, to_python_with_map
from .vm import run as vm_run


def run_source(
    source: str,
    *,
    stdin: str | None = None,
    emit: str | None = None,
    optimize_flag: bool = False,
    sourcemap: bool = False,
) -> str:
    parser = Parser()
    program = parser.parse(source)
    if optimize_flag:
        program = optimize(program)
    if emit == "python":
        if sourcemap:
            code, sm = to_python_with_map(program)
            # attach simple inline sourcemap as a comment block
            sm_lines = [
                f"# map {py}:{src if src is not None else 'None'}" for py, src in sm
            ]
            return code + "\n" + "\n".join(sm_lines) + "\n"
        return to_python(program)
    interpreter = Interpreter()
    return interpreter.run(program, stdin=stdin)


def run_file(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        # Temporarily run with CWD set to the file's directory so imports resolve naturally
        old_cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(os.path.abspath(path)) or old_cwd)
            output = run_source(source)
        finally:
            os.chdir(old_cwd)
        if output:
            sys.stdout.write(output)
        return 0
    except SupError as e:
        sys.stderr.write(str(e) + "\n")
        return 2
    except Exception as e:
        # Catch-all: attempt to remap using sourcemap
        try:
            msg = remap_exception(e)
        except Exception:
            msg = str(e)
        sys.stderr.write(msg + "\n")
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

    # Load incremental cache manifest
    manifest_path = os.path.join(out_dir, ".sup_cache.json")
    try:
        with open(manifest_path, encoding="utf-8") as mf:
            manifest: dict[str, dict[str, object]] = json.load(mf)
    except Exception:
        manifest = {}

    # Ensure the entry file directory is searched for imports by default
    entry_dir = os.path.dirname(os.path.abspath(entry_file))
    prev_sup_path = os.environ.get("SUP_PATH")
    extra_path = (
        entry_dir if not prev_sup_path else entry_dir + os.pathsep + prev_sup_path
    )
    os.environ["SUP_PATH"] = extra_path

    def transpile_file(path: str) -> None:
        src = open(path, encoding="utf-8").read()
        # Identify module/output paths
        module_name = os.path.splitext(os.path.basename(path))[0]
        py_module = sanitize_module(module_name)
        py_path = os.path.join(out_dir, f"{py_module}.py")
        # Compute hash for cache comparison
        src_hash = hashlib.sha256(src.encode("utf-8")).hexdigest()
        cached = manifest.get(module_name)
        if (
            cached is not None
            and isinstance(cached, dict)
            and cached.get("src_hash") == src_hash
            and os.path.exists(py_path)
        ):
            # Reuse cached imports without re-parsing
            imports = {str(x) for x in (cached.get("imports") or [])}
        else:
            # Parse and emit with sourcemap file
            program = parser.parse(src)
            py_code, smap = to_python_with_map(program)
            map_name = f"{py_module}.py.map"
            py_code = py_code + f"\n# sourceMappingURL={map_name}\n"
            with open(py_path, "w", encoding="utf-8") as f:
                f.write(py_code)
            # Write map
            map_path = os.path.join(out_dir, map_name)
            src_name = os.path.basename(path)  # include .sup for clearer mapping
            with open(map_path, "w", encoding="utf-8") as mf:
                mf.write(build_sourcemap_json(py_code, src_name, src, smap))
            # Gather imports for dependency traversal
            imports: set[str] = set()
            _gather_imports(program, imports)
            # Update manifest entry
            manifest[module_name] = {
                "src_path": path,
                "src_hash": src_hash,
                "imports": sorted(list(imports)),
            }
        nonlocal entry_module
        nonlocal entry_module_py
        if entry_module is None:
            entry_module = module_name
            entry_module_py = py_module
        # Recurse into imports
        for mod in imports:
            if mod not in visited:
                visited.add(mod)
                mod_path = _resolve_module_path(mod)
                transpile_file(mod_path)

    try:
        visited.add(os.path.splitext(os.path.basename(entry_file))[0])
        transpile_file(entry_file)
    finally:
        # Restore SUP_PATH
        if prev_sup_path is None:
            os.environ.pop("SUP_PATH", None)
        else:
            os.environ["SUP_PATH"] = prev_sup_path
    # Persist incremental cache manifest
    try:
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)
    except Exception:
        pass
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

    # Route scaffold command: sup init myapp
    if len(argv) > 0 and argv[0] == "init":
        p_init = argparse.ArgumentParser(
            prog="sup init", description="Scaffold a new SUP project"
        )
        p_init.add_argument("name", help="Project folder name")
        init_args = p_init.parse_args(argv[1:])
        proj_dir = os.path.abspath(init_args.name)
        os.makedirs(proj_dir, exist_ok=True)
        # Create a simple project: main.sup, sup.json, README
        main_sup = os.path.join(proj_dir, "main.sup")
        if not os.path.exists(main_sup):
            with open(main_sup, "w", encoding="utf-8") as f:
                f.write(
                    """sup
print "Hello from SUP"
bye
"""
                )
        meta = os.path.join(proj_dir, "sup.json")
        if not os.path.exists(meta):
            with open(meta, "w", encoding="utf-8") as f:
                f.write(
                    "{"
                    "name"
                    ": "
                    "%s"
                    ", "
                    "version"
                    ": "
                    "0.1.0"
                    ", "
                    "entry"
                    ": "
                    "main.sup"
                    "}" % init_args.name
                )
        readme = os.path.join(proj_dir, "README.md")
        if not os.path.exists(readme):
            with open(readme, "w", encoding="utf-8") as f:
                f.write(
                    f"# {init_args.name}\n\nBootstrap project created by sup init.\n"
                )
        print(f"Initialized SUP project in {proj_dir}")
        return 0
    # Package manager: build/lock/test/publish
    if len(argv) > 0 and argv[0] == "build":
        p = argparse.ArgumentParser(
            prog="sup build", description="Build (transpile) project"
        )
        p.add_argument("entry", help="Entry .sup file (e.g., main.sup)")
        p.add_argument("--out", default="dist_sup", help="Output directory")
        args_b = p.parse_args(argv[1:])
        try:
            transpile_project(args_b.entry, args_b.out)
            print(f"Built to {args_b.out}")
            return 0
        except Exception as e:
            sys.stderr.write(str(e) + "\n")
            return 2
    if len(argv) > 0 and argv[0] == "lock":
        p = argparse.ArgumentParser(
            prog="sup lock", description="Generate sup.lock for reproducible builds"
        )
        p.add_argument("entry", help="Entry .sup file")
        args_l = p.parse_args(argv[1:])
        parser = Parser()
        src = open(args_l.entry, encoding="utf-8").read()
        program = parser.parse(src)
        mods: set[str] = set()
        _gather_imports(program, mods)
        # include entry module too
        mods.add(os.path.splitext(os.path.basename(args_l.entry))[0])
        lock: dict[str, dict[str, str]] = {"modules": {}}
        for m in sorted(mods):
            try:
                path = _resolve_module_path(m)
            except FileNotFoundError:
                continue
            data = open(path, "rb").read()
            sha = hashlib.sha256(data).hexdigest()
            lock["modules"][m] = {"path": path, "sha256": sha}
        with open("sup.lock", "w", encoding="utf-8") as f:
            json.dump(lock, f, indent=2)
        print("Wrote sup.lock")
        return 0
    if len(argv) > 0 and argv[0] == "test":
        p = argparse.ArgumentParser(
            prog="sup test", description="Run .sup files in a directory"
        )
        p.add_argument(
            "dir", nargs="?", default="tests", help="Directory with .sup tests"
        )
        args_t = p.parse_args(argv[1:])
        if not os.path.isdir(args_t.dir):
            print(f"No test directory {args_t.dir}")
            return 0
        files = sorted(glob.glob(os.path.join(args_t.dir, "*.sup")))
        passed = 0
        for fp in files:
            rc = run_file(fp)
            if rc == 0:
                passed += 1
        total = len(files)
        print(f"Passed {passed}/{total}")
        return 0 if passed == total else 1
    if len(argv) > 0 and argv[0] == "publish":
        p = argparse.ArgumentParser(
            prog="sup publish", description="Create a source tarball in dist_sup"
        )
        p.add_argument(
            "project", nargs="?", default=".", help="Project directory with sup.json"
        )
        args_p = p.parse_args(argv[1:])
        proj = os.path.abspath(args_p.project)
        meta_path = os.path.join(proj, "sup.json")
        if not os.path.exists(meta_path):
            sys.stderr.write("sup.json not found\n")
            return 2
        meta = json.load(open(meta_path, encoding="utf-8"))
        name = meta.get("name", os.path.basename(proj))
        version = meta.get("version", "0.1.0")
        out_dir = os.path.join(proj, "dist_sup")
        os.makedirs(out_dir, exist_ok=True)
        tgt = os.path.join(out_dir, f"{name}-{version}.tar.gz")
        with tarfile.open(tgt, "w:gz") as tar:
            for root, _, files in os.walk(proj):
                for fn in files:
                    if fn.endswith((".sup", ".md", ".json", ".lock")):
                        full = os.path.join(root, fn)
                        arc = os.path.relpath(full, proj)
                        tar.add(full, arcname=arc)
        print(f"Created {tgt}")
        return 0

    # Default mode: run a file or start a REPL; optional --emit python; --version
    parser = argparse.ArgumentParser(prog="sup", description="Sup language CLI")
    parser.add_argument("file", nargs="?", help="Path to .sup file to run")
    parser.add_argument(
        "args", nargs=argparse.REMAINDER, help="Arguments passed to program"
    )
    parser.add_argument(
        "--emit", choices=["python"], help="Transpile to target language and print"
    )
    parser.add_argument("--opt", action="store_true", help="Enable AST optimizations")
    parser.add_argument(
        "--sourcemap",
        action="store_true",
        help="Include sourcemap comments when emitting",
    )
    parser.add_argument(
        "--backend",
        choices=["interp", "vm"],
        default="interp",
        help="Execution backend for run mode",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Run with interactive step debugger"
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.file:
        # Expose remaining args to program via SUP_ARGS
        if args.args:
            os.environ["SUP_ARGS"] = " ".join(a for a in args.args if a.strip())
        if args.emit:
            with open(args.file, encoding="utf-8") as f:
                src = f.read()
            try:
                out = run_source(
                    src,
                    emit=args.emit,
                    optimize_flag=args.opt,
                    sourcemap=args.sourcemap,
                )
                if out:
                    sys.stdout.write(out)
                return 0
            except SupError as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        # normal run
        if args.debug:
            with open(args.file, encoding="utf-8") as f:
                src = f.read()
            program = Parser().parse(src)
            dbg = Debugger(program, src)
            try:
                dbg.run()
                return 0
            except SupError as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        if args.opt or args.backend != "interp":
            with open(args.file, encoding="utf-8") as f:
                src = f.read()
            try:
                if args.backend == "vm":
                    program = Parser().parse(src)
                    if args.opt:
                        program = optimize(program)
                    try:
                        out = vm_run(program)
                    except NotImplementedError as e:
                        sys.stderr.write(str(e) + "\n")
                        return 2
                else:
                    out = run_source(src, optimize_flag=args.opt)
                if out:
                    sys.stdout.write(out)
                return 0
            except SupError as e:
                sys.stderr.write(str(e) + "\n")
                return 2
        return run_file(args.file)
    return repl()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
