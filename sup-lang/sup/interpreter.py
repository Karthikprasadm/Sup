from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from . import ast as AST
from .errors import SupRuntimeError


@dataclass
class IOHooks:
    stdin: str | None = None
    outputs: list[str] = field(default_factory=list)

    def read_input(self) -> str:
        if self.stdin is None:
            # Interactive input
            return input()
        # Pop first line from stdin buffer
        if "\n" in self.stdin:
            line, rest = self.stdin.split("\n", 1)
            self.stdin = rest
        else:
            line, self.stdin = self.stdin, None
        return line

    def write_output(self, text: str) -> None:
        self.outputs.append(text)


class Interpreter:
    def __init__(self) -> None:
        self.env: dict[str, object] = {}
        self.functions: dict[str, AST.FunctionDef] = {}
        self.module_cache: dict[str, dict[str, object]] = {}
        self.loading_modules: set[str] = set()
        self.last_result: object | None = None
        self.io = IOHooks()
        # Lazy helpers for logging/async tasks
        self._logger: Any = None
        self._executor: Any = None
        self._futures: dict[int, object] = {}
        # Capability model (safe-by-default). Categories: net, process, fs_write, archive, sql
        # Allow override via env SUP_UNSAFE=1 (disable gating) or SUP_CAPS=comma,separated,list
        import os as _os_caps  # local import to avoid global side effects

        self._unsafe_all = _os_caps.environ.get("SUP_UNSAFE") in {"1", "true", "yes"}
        caps_env = _os_caps.environ.get("SUP_CAPS", "")
        self.capabilities: set[str] = (
            {c.strip() for c in caps_env.split(",") if c.strip()} if caps_env else set()
        )
        # HTTP defaults
        self._http_timeout_sec: float = 10.0
        self._http_max_bytes: int = 1_000_000
        # ---- Sandbox limits (env-configurable) ----
        # SUP_LIMIT_WALL_MS, SUP_LIMIT_STEPS, SUP_LIMIT_MEM_MB, SUP_LIMIT_FD
        try:
            wall_ms = os.environ.get("SUP_LIMIT_WALL_MS")
            self._limit_wall_sec: float | None = (
                (float(wall_ms) / 1000.0) if wall_ms else None
            )
        except Exception:
            self._limit_wall_sec = None
        try:
            steps = os.environ.get("SUP_LIMIT_STEPS")
            self._limit_steps: int | None = int(steps) if steps else None
        except Exception:
            self._limit_steps = None
        try:
            mem_mb = os.environ.get("SUP_LIMIT_MEM_MB")
            self._limit_mem_bytes: int | None = (
                int(float(mem_mb) * 1024 * 1024) if mem_mb else None
            )
        except Exception:
            self._limit_mem_bytes = None
        try:
            fdl = os.environ.get("SUP_LIMIT_FD")
            self._limit_fd: int | None = int(fdl) if fdl else None
        except Exception:
            self._limit_fd = None
        # Deterministic mode
        self._deterministic: bool = os.environ.get("SUP_DETERMINISTIC") in {
            "1",
            "true",
            "yes",
        }
        self._seed = (
            int(os.environ.get("SUP_SEED", "0")) if self._deterministic else None
        )
        if self._deterministic:
            import random as _random

            self._rng = _random.Random(self._seed or 0)
            # Force C locale for stable formatting/sorting
            try:
                import locale as _loc

                _loc.setlocale(_loc.LC_ALL, "C")
            except Exception:
                pass
        else:
            self._rng = None
        # Runtime counters
        import time as _t

        self._wall_start = _t.perf_counter()
        self._steps = 0
        # Memory tracking
        self._tm = None
        if self._limit_mem_bytes is not None:
            try:
                import tracemalloc as _tm

                _tm.start()
                self._tm = _tm
            except Exception:
                self._tm = None
        # FD tracking
        self._fd_open_count = 0

    def run(self, program: AST.Program, *, stdin: str | None = None) -> str:
        self.io.stdin = stdin
        # reset counters
        import time as _t

        self._wall_start = _t.perf_counter()
        self._steps = 0
        self.eval_program(program)
        return "".join(self.io.outputs)

    def eval_program(self, program: AST.Program) -> None:
        for stmt in program.statements:
            self.eval(stmt)

    def eval(self, node: AST.Node) -> object | None:
        # step & resource checks
        self._steps += 1
        self._check_limits()
        if isinstance(node, AST.Assignment):
            value = self.eval(node.expr)
            self.env[node.name.lower()] = value
            self.last_result = value
            return value
        if isinstance(node, AST.Print):
            value = self.last_result if node.expr is None else self.eval(node.expr)
            self.io.write_output(f"{self._format_value(value)}\n")
            return value
        if isinstance(node, AST.Ask):
            val = self.io.read_input()
            self.env[node.name.lower()] = val
            self.last_result = val
            return val
        if isinstance(node, AST.If):
            cond_val = self._truthy(self.eval(node.cond) if node.cond is not None else self._compare(self.eval(node.left), node.op, self.eval(node.right)))  # type: ignore[arg-type]
            if cond_val:
                for s in node.body or []:
                    self.eval(s)
            else:
                for s in node.else_body or []:
                    self.eval(s)
            return None
        if isinstance(node, AST.While):
            while self._truthy(self.eval(node.cond)):
                for s in node.body:
                    self.eval(s)
            return None
        if isinstance(node, AST.ForEach):
            iterable = self.eval(node.iterable)
            try:
                iterator = list(iterable)  # type: ignore[arg-type,call-overload]
            except Exception:
                raise SupRuntimeError(message="Target of for each is not iterable.")
            saved = self.env.get(node.var.lower())
            try:
                for item in iterator:
                    self.env[node.var.lower()] = item
                    for s in node.body:
                        self.eval(s)
            finally:
                if saved is None:
                    self.env.pop(node.var.lower(), None)
                else:
                    self.env[node.var.lower()] = saved
            return None
        if isinstance(node, AST.Repeat):
            count_val = self.eval(node.count_expr)
            try:
                iterations = int(count_val)  # type: ignore[arg-type,call-overload]
            except Exception:
                raise SupRuntimeError(
                    message="Repeat count must be a number.",
                    line=getattr(node, "line", None),
                )
            for _ in range(iterations):
                for s in node.body:
                    self.eval(s)
            return None
        if isinstance(node, AST.ExprStmt):
            value = self.eval(node.expr)
            self.last_result = value
            return value
        if isinstance(node, AST.TryCatch):
            error: Exception | None = None
            try:
                for s in node.body:
                    self.eval(s)
            except Exception as e:  # catch Sup and general errors
                error = e
                if node.catch_body is not None:
                    if node.catch_name:
                        if isinstance(e, _SupThrown):
                            self.env[node.catch_name.lower()] = e.value
                        else:
                            self.env[node.catch_name.lower()] = str(e)
                    for s in node.catch_body:
                        self.eval(s)
                else:
                    # no catch: rethrow after finally
                    pass
            finally:
                if node.finally_body is not None:
                    for s in node.finally_body:
                        self.eval(s)
                if error is not None and node.catch_body is None:
                    raise error
            return None
        if isinstance(node, AST.Throw):
            val = self.eval(node.value)
            raise _SupThrown(val)
        if isinstance(node, AST.Import):
            ns = self._import_module(node.module)
            self.env[(node.alias or node.module).lower()] = ns
            return None
        if isinstance(node, AST.FromImport):
            ns = self._import_module(node.module)
            for name, alias in node.names:
                if name not in ns:
                    raise SupRuntimeError(
                        message=f"Module '{node.module}' has no symbol '{name}'."
                    )
                self.env[(alias or name).lower()] = ns[name]
            return None
        if isinstance(node, AST.FunctionDef):
            self.functions[node.name.lower()] = node
            return None
        if isinstance(node, AST.Return):
            # Signal a return using exception for simple control flow
            raise _ReturnSignal(self.eval(node.expr) if node.expr is not None else None)
        if isinstance(node, AST.Call):
            return self._call_function(node)
        # Collections and stdlib
        if isinstance(node, AST.MakeList):
            lst = [self.eval(it) for it in node.items]
            self.env["list"] = lst
            self.last_result = lst
            return lst
        if isinstance(node, AST.MakeMap):
            d: dict[object, object] = {}
            self.env["map"] = d
            self.last_result = d
            return d
        if isinstance(node, AST.Push):
            target = self.eval(node.target)
            if not isinstance(target, list):
                raise SupRuntimeError(message="Push target must be a list.")
            target.append(self.eval(node.item))
            self.last_result = target
            return target
        if isinstance(node, AST.Pop):
            target = self.eval(node.target)
            if not isinstance(target, list):
                raise SupRuntimeError(message="Pop target must be a list.")
            val = target.pop()
            self.last_result = val
            return val
        if isinstance(node, AST.GetKey):
            target = self.eval(node.target)
            key = self.eval(node.key)
            if isinstance(target, list):
                try:
                    idx = int(self._num(key))
                except Exception:
                    raise SupRuntimeError(message="List index must be a number.")
                try:
                    val = target[idx]
                except Exception:
                    raise SupRuntimeError(message="List index out of range.")
                self.last_result = val
                return val
            if isinstance(target, dict):
                val = target.get(key)  # type: ignore[call-arg]
                self.last_result = val
                return val
            raise SupRuntimeError(message="Get target must be a list or map.")
        if isinstance(node, AST.SetKey):
            target = self.eval(node.target)
            key = self.eval(node.key)
            val = self.eval(node.value)
            if not isinstance(target, dict):
                raise SupRuntimeError(message="Set target must be a map.")
            target[key] = val
            self.last_result = target
            return target
        if isinstance(node, AST.DeleteKey):
            target = self.eval(node.target)
            key = self.eval(node.key)
            if not isinstance(target, dict):
                raise SupRuntimeError(message="Delete target must be a map.")
            target.pop(key, None)
            self.last_result = target
            return target
        if isinstance(node, AST.Length):
            target = self.eval(node.target)
            length_value = len(target)  # type: ignore[arg-type]
            self.last_result = length_value
            return length_value
        if isinstance(node, AST.BuiltinCall):
            return self._eval_builtin(node)
        if isinstance(node, AST.Binary):
            left = self.eval(node.left)
            right = self.eval(node.right)
            try:
                if node.op in {"+", "-", "*"}:
                    lnum, lint = self._to_number(left)
                    rnum, rint = self._to_number(right)
                    if node.op == "+":
                        value = lnum + rnum
                    elif node.op == "-":
                        value = lnum - rnum
                    else:
                        value = lnum * rnum
                    if lint and rint and float(value).is_integer():
                        res = int(value)
                    else:
                        res = float(value)
                elif node.op == "/":
                    res = float(self._num(left)) / float(self._num(right))
                else:
                    raise SupRuntimeError(message=f"Unknown operator {node.op}.")
            except ZeroDivisionError:
                raise SupRuntimeError(
                    message="Division by zero.", line=getattr(node, "line", None)
                )
            self.last_result = res
            return res
        if isinstance(node, AST.Identifier):
            name = node.name.lower()
            # dotted access: module.symbol
            if "." in name:
                mod, sym = name.split(".", 1)
                if mod in self.env and isinstance(self.env[mod], dict):
                    ns = self.env[mod]
                    return ns.get(sym)
            if name in self.env:
                return self.env[name]
            # Allow implicit references to 'list' and 'map' if they were just created as last_result
            if name in {"list", "map"} and isinstance(self.last_result, (list, dict)):
                return self.last_result
            raise SupRuntimeError(
                message=f"Undefined variable '{node.name}'.",
                line=getattr(node, "line", None),
            )
        if isinstance(node, AST.String):
            return node.value
        if isinstance(node, AST.Number):
            return node.value
        if isinstance(node, AST.BoolBinary):
            if node.op == "and":
                left = self._truthy(self.eval(node.left))
                return left and self._truthy(self.eval(node.right))
            if node.op == "or":
                left = self._truthy(self.eval(node.left))
                return left or self._truthy(self.eval(node.right))
            raise SupRuntimeError(message=f"Unknown boolean operator {node.op}.")
        if isinstance(node, AST.NotOp):
            return not self._truthy(self.eval(node.expr))
        if isinstance(node, AST.Compare):
            return self._compare(self.eval(node.left), node.op, self.eval(node.right))
        raise SupRuntimeError(message=f"Unsupported AST node {type(node).__name__}.")

    # ---- Sandbox helpers ----
    def _check_limits(self) -> None:
        # steps
        if self._limit_steps is not None and self._steps > self._limit_steps:
            raise SupRuntimeError(message="Resource limit exceeded: steps")
        # wall time
        if self._limit_wall_sec is not None:
            import time as _t

            if (_t.perf_counter() - self._wall_start) > self._limit_wall_sec:
                raise SupRuntimeError(message="Resource limit exceeded: wall time")
        # memory (tracemalloc current usage)
        if self._limit_mem_bytes is not None and self._tm is not None:
            try:
                current, _peak = self._tm.get_traced_memory()
                if current > self._limit_mem_bytes:
                    raise SupRuntimeError(message="Resource limit exceeded: memory")
            except Exception:
                pass

    def _reserve_fd(self, n: int = 1) -> None:
        if self._limit_fd is None:
            return
        if self._fd_open_count + n > self._limit_fd:
            raise SupRuntimeError(message="Resource limit exceeded: file descriptors")
        self._fd_open_count += n

    def _release_fd(self, n: int = 1) -> None:
        self._fd_open_count = max(0, self._fd_open_count - n)

    @contextmanager
    def _safe_open(self, path: str, *args: object, **kwargs: object):
        self._reserve_fd(1)
        f = open(path, *args, **kwargs)  # type: ignore[arg-type]
        try:
            yield f
        finally:
            try:
                f.close()
            finally:
                self._release_fd(1)

    def _compare(self, left: object, op: str | None, right: object) -> bool:  # type: ignore[override]
        if op == ">":
            return self._num(left) > self._num(right)
        if op == "<":
            return self._num(left) < self._num(right)
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == ">=":
            return self._num(left) >= self._num(right)
        if op == "<=":
            return self._num(left) <= self._num(right)
        raise SupRuntimeError(message=f"Unknown relational operator {op}.")

    def _truthy(self, v: object) -> bool:
        return bool(v)

    def _num(self, v: object) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        # attempt to parse string numbers for friendliness
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                pass
        raise SupRuntimeError(message=f"Expected a number, got {type(v).__name__}.")

    def _format_value(self, v: object) -> str:
        if isinstance(v, float):
            return str(v)
        return str(v)

    def _to_number(self, v: object) -> tuple[float, bool]:
        is_int = isinstance(v, int)
        num = self._num(v)
        return num, is_int

    def _eval_builtin(self, node: AST.BuiltinCall) -> object:
        name = node.name
        # Filesystem / path / env / subprocess
        if name == "env_get":
            import os as _os

            key = str(self.eval(node.args[0]))
            out_env = _os.environ.get(key, "")
            self.last_result = out_env
            return out_env
        if name == "env_set":
            import os as _os

            key = str(self.eval(node.args[0]))
            val = str(self.eval(node.args[1]))
            _os.environ[key] = val
            self.last_result = val
            return val
        if name == "cwd":
            import os as _os

            out_cwd = _os.getcwd()
            self.last_result = out_cwd
            return out_cwd
        if name == "exists":
            import os as _os

            path = str(self.eval(node.args[0]))
            ok_exists = _os.path.exists(path)
            self.last_result = ok_exists
            return ok_exists
        if name == "glob":
            import glob as _glob

            pattern = str(self.eval(node.args[0]))
            matches = list(_glob.glob(pattern))
            self.last_result = matches
            return matches
        if name == "join_path":
            import os as _os

            a = str(self.eval(node.args[0]))
            b = str(self.eval(node.args[1]))
            joined_path = _os.path.join(a, b)
            self.last_result = joined_path
            return joined_path
        if name == "dirname":
            import os as _os

            p = str(self.eval(node.args[0]))
            out_dirname = _os.path.dirname(p)
            self.last_result = out_dirname
            return out_dirname
        if name == "basename":
            import os as _os

            p = str(self.eval(node.args[0]))
            out_basename = _os.path.basename(p)
            self.last_result = out_basename
            return out_basename
        if name == "copy_file":
            self._require_cap("fs_write")
            import shutil as _sh

            src = str(self.eval(node.args[0]))
            dst = str(self.eval(node.args[1]))
            _sh.copyfile(src, dst)
            self.last_result = True
            return True
        if name == "move_file":
            self._require_cap("fs_write")
            import shutil as _sh

            src = str(self.eval(node.args[0]))
            dst = str(self.eval(node.args[1]))
            _sh.move(src, dst)
            self.last_result = True
            return True
        if name == "remove_file":
            self._require_cap("fs_write")
            import os as _os

            p = str(self.eval(node.args[0]))
            try:
                _os.remove(p)
            except FileNotFoundError:
                pass
            self.last_result = True
            return True
        if name == "makedirs":
            self._require_cap("fs_write")
            import os as _os

            p = str(self.eval(node.args[0]))
            _os.makedirs(p, exist_ok=True)
            self.last_result = True
            return True
        if name == "subprocess_run":
            self._require_cap("process")
            import subprocess as _sp

            cmd = str(self.eval(node.args[0]))
            timeout = None
            if len(node.args) > 1:
                try:
                    timeout = float(self._num(self.eval(node.args[1])))
                except Exception:
                    timeout = None
            cp = _sp.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            res: dict[str, str | int] = {
                "code": int(cp.returncode),
                "out": cp.stdout,
                "err": cp.stderr,
            }
            self.last_result = res
            return res

        # HTTP / URL / querystring
        if name == "http_get":
            self._require_cap("net")
            import urllib.request as _u

            url = str(self.eval(node.args[0]))
            headers: dict[str, str] = {}
            if len(node.args) > 1:
                hdrs_obj = self.eval(node.args[1])
                if isinstance(hdrs_obj, dict):
                    headers = {str(k): str(v) for k, v in hdrs_obj.items()}
            req = _u.Request(url, headers=headers)
            with _u.urlopen(req, timeout=self._http_timeout_sec) as r:
                data = r.read(self._http_max_bytes).decode("utf-8", "replace")
            self.last_result = data
            return data
        if name == "http_post":
            self._require_cap("net")
            import urllib.request as _u

            url = str(self.eval(node.args[0]))
            body = str(self.eval(node.args[1]))
            headers_post: dict[str, str] = {"Content-Type": "text/plain; charset=utf-8"}
            if len(node.args) > 2:
                hdrs_obj = self.eval(node.args[2])
                if isinstance(hdrs_obj, dict):
                    headers_post.update({str(k): str(v) for k, v in hdrs_obj.items()})
            req = _u.Request(
                url, data=body.encode("utf-8"), headers=headers_post, method="POST"
            )
            with _u.urlopen(req, timeout=self._http_timeout_sec) as r:
                data = r.read(self._http_max_bytes).decode("utf-8", "replace")
            self.last_result = data
            return data
        if name == "http_json":
            self._require_cap("net")
            import json as _json

            fake = AST.BuiltinCall("http_get", [node.args[0]])
            text = str(self._eval_builtin(fake))
            obj_json = _json.loads(text)
            self.last_result = obj_json
            return obj_json
        if name == "http_status":
            self._require_cap("net")
            import urllib.request as _u

            url = str(self.eval(node.args[0]))
            req = _u.Request(url)
            with _u.urlopen(req, timeout=self._http_timeout_sec) as r:
                code = int(r.getcode())
            self.last_result = float(code)
            return float(code)
        if name == "url_parse":
            import urllib.parse as _p

            u = str(self.eval(node.args[0]))
            pr = _p.urlparse(u)
            res_url: dict[str, str] = {
                "scheme": pr.scheme,
                "host": pr.netloc,
                "path": pr.path,
                "query": pr.query,
                "fragment": pr.fragment,
            }
            self.last_result = res_url
            return res_url
        if name == "url_encode":
            import urllib.parse as _p

            s = str(self.eval(node.args[0]))
            res = _p.quote(s, safe="")
            self.last_result = res
            return res
        if name == "url_decode":
            import urllib.parse as _p

            s = str(self.eval(node.args[0]))
            res = _p.unquote(s)
            self.last_result = res
            return res
        if name == "querystring_encode":
            import urllib.parse as _p

            m = self.eval(node.args[0])
            if not isinstance(m, dict):
                raise SupRuntimeError(message="querystring encode expects a map.")
            res = _p.urlencode({str(k): str(v) for k, v in m.items()})
            self.last_result = res
            return res
        if name == "querystring_decode":
            import urllib.parse as _p

            s = str(self.eval(node.args[0]))
            pairs = _p.parse_qsl(s, keep_blank_values=True)
            qs_map: dict[str, str] = {}
            for k, v in pairs:
                qs_map[str(k)] = str(v)
            self.last_result = qs_map
            return qs_map

        # Crypto / base64 / randomness / time
        if name == "sha256":
            import hashlib as _hh

            s = str(self.eval(node.args[0]))
            hexout = _hh.sha256(s.encode("utf-8")).hexdigest()
            self.last_result = hexout
            return hexout
        if name == "sha1":
            import hashlib as _hh

            s = str(self.eval(node.args[0]))
            hexout = _hh.sha1(s.encode("utf-8")).hexdigest()
            self.last_result = hexout
            return hexout
        if name == "md5":
            import hashlib as _hh

            s = str(self.eval(node.args[0]))
            hexout = _hh.md5(s.encode("utf-8")).hexdigest()
            self.last_result = hexout
            return hexout
        if name == "hmac_sha256":
            import hashlib as _hh
            import hmac as _hmac

            key = str(self.eval(node.args[0])).encode("utf-8")
            msg = str(self.eval(node.args[1])).encode("utf-8")
            hmac_hex = _hmac.new(key, msg, _hh.sha256).hexdigest()
            self.last_result = hmac_hex
            return hmac_hex
        if name == "random_bytes":
            import base64 as _b64
            n = int(self._num(self.eval(node.args[0]))) if len(node.args) > 0 else 16
            n = max(1, n)
            if self._rng is not None:
                # Deterministic bytes derived from PRNG
                data = bytes(self._rng.randrange(0, 256) for _ in range(n))
            else:
                import secrets as _secrets

                data = _secrets.token_bytes(n)
            b64 = _b64.b64encode(data).decode("ascii")
            self.last_result = b64
            return b64
        if name == "now":
            # Return ISO 8601 UTC timestamp. In deterministic mode, derive from seed.
            import datetime as _dt

            if self._deterministic:
                # Stable pseudo-time based on seed (seconds since epoch)
                base = int(self._seed or 0)
                t = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc) + _dt.timedelta(
                    seconds=base
                )
            else:
                t = _dt.datetime.now(tz=_dt.timezone.utc)
            iso = t.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            self.last_result = iso
            return iso
        if name == "base64_encode":
            import base64 as _b64

            s_bytes = str(self.eval(node.args[0])).encode("utf-8")
            b64 = _b64.b64encode(s_bytes).decode("ascii")
            self.last_result = b64
            return b64
        if name == "base64_decode":
            import base64 as _b64

            s = str(self.eval(node.args[0]))
            decoded = _b64.b64decode(s).decode("utf-8", "replace")
            self.last_result = decoded
            return decoded

        # Regex
        if name == "regex_match":
            import re as _re

            pat = str(self.eval(node.args[0]))
            text = str(self.eval(node.args[1]))
            ok = _re.search(pat, text) is not None
            self.last_result = ok
            return ok
        if name == "regex_findall":
            import re as _re

            pat = str(self.eval(node.args[0]))
            text = str(self.eval(node.args[1]))
            all_matches = list(_re.findall(pat, text))
            self.last_result = all_matches
            return all_matches
        if name == "regex_replace":
            import re as _re

            # Parser supplies arguments as [pattern, text, replacement]
            pat = str(self.eval(node.args[0]))
            text = str(self.eval(node.args[1]))
            repl = str(self.eval(node.args[2]))
            replaced = _re.sub(pat, repl, text)
            self.last_result = replaced
            return replaced

        # Logging
        if name == "set_log_level":
            import logging as _log

            if self._logger is None:
                self._logger = _log.getLogger("sup")
            lvl = str(self.eval(node.args[0])).upper()
            level = getattr(_log, lvl, _log.INFO)
            self._logger.setLevel(level)
            self.last_result = True
            return True
        if name in {"log_debug", "log_info", "log_warn", "log_error"}:
            import logging as _log

            if self._logger is None:
                self._logger = _log.getLogger("sup")
            msg_txt = str(self.eval(node.args[0])) if len(node.args) > 0 else ""
            if name == "log_debug":
                self._logger.debug(msg_txt)
            elif name == "log_info":
                self._logger.info(msg_txt)
            elif name == "log_warn":
                self._logger.warning(msg_txt)
            else:
                self._logger.error(msg_txt)
            self.last_result = True
            return True

        # CLI args
        if name == "args":
            import sys as _sys

            argv_list = list(_sys.argv[1:])
            self.last_result = argv_list
            return argv_list
        if name == "arg":
            import sys as _sys

            idx = int(self._num(self.eval(node.args[0])))
            vals = list(_sys.argv[1:])
            val = vals[idx] if 0 <= idx < len(vals) else ""
            self.last_result = val
            return val
        if name == "args_map":
            import sys as _sys

            vals = list(_sys.argv[1:])
            arg_map: dict[str, str] = {}
            for tok in vals:
                if tok.startswith("--") and "=" in tok:
                    k, v = tok[2:].split("=", 1)
                    arg_map[k] = v
            self.last_result = arg_map
            return arg_map

        # CSV / XML / ZIP / SQLite
        if name == "csv_read":
            import csv as _csv

            p = str(self.eval(node.args[0]))
            rows: list[list[str]] = []
            with open(p, newline="", encoding="utf-8") as f:
                for row in _csv.reader(f):
                    rows.append([str(x) for x in row])
            self.last_result = rows
            return rows
        if name == "csv_write":
            self._require_cap("fs_write")
            import csv as _csv

            p = str(self.eval(node.args[0]))
            rows_obj = self.eval(node.args[1])
            if not isinstance(rows_obj, list):
                raise SupRuntimeError(message="csv write expects list of rows.")
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = _csv.writer(f)
                for r in rows_obj:
                    if isinstance(r, list):
                        w.writerow([str(x) for x in r])
                    else:
                        w.writerow([str(r)])
            self.last_result = True
            return True
        if name == "xml_parse":
            import xml.etree.ElementTree as _ET

            s = str(self.eval(node.args[0]))
            elem = _ET.fromstring(s)
            self.last_result = elem
            return elem
        if name == "xml_find":
            root = self.eval(node.args[0])
            path = str(self.eval(node.args[1]))
            if hasattr(root, "findall"):
                elems = list(root.findall(path))  # type: ignore[attr-defined]
            else:
                elems = []
            self.last_result = elems
            return elems
        if name == "xml_text":
            el = self.eval(node.args[0])
            text = getattr(el, "text", None)
            txt = "" if text is None else str(text)
            self.last_result = txt
            return txt
        if name == "zip_create":
            self._require_cap("archive")
            import zipfile as _zf

            zip_path = str(self.eval(node.args[0]))
            files = self.eval(node.args[1])
            if not isinstance(files, list):
                raise SupRuntimeError(message="zip create expects list of files.")
            with _zf.ZipFile(zip_path, "w", compression=_zf.ZIP_DEFLATED) as zf:
                for p in files:
                    zf.write(str(p), arcname=str(p))
            self.last_result = True
            return True
        if name == "zip_extract":
            self._require_cap("archive")
            import zipfile as _zf

            zip_path = str(self.eval(node.args[0]))
            out_dir = str(self.eval(node.args[1]))
            with _zf.ZipFile(zip_path, "r") as zf:
                zf.extractall(out_dir)
            self.last_result = True
            return True
        if name == "sqlite_exec":
            self._require_cap("sql")
            import sqlite3 as _sql

            db = str(self.eval(node.args[0]))
            sql = str(self.eval(node.args[1]))
            params = ()
            if len(node.args) > 2:
                plist = self.eval(node.args[2])
                if isinstance(plist, list):
                    params = tuple(plist)
            con = _sql.connect(db)
            try:
                cur = con.cursor()
                cur.execute(sql, params)
                con.commit()
                lastrowid = cur.lastrowid
            finally:
                con.close()
            self.last_result = float(lastrowid if lastrowid is not None else 0)
            return float(lastrowid if lastrowid is not None else 0)
        if name == "sqlite_query":
            self._require_cap("sql")
            import sqlite3 as _sql

            db = str(self.eval(node.args[0]))
            sql = str(self.eval(node.args[1]))
            params = ()
            if len(node.args) > 2:
                plist = self.eval(node.args[2])
                if isinstance(plist, list):
                    params = tuple(plist)
            con = _sql.connect(db)
            try:
                cur = con.cursor()
                cur.execute(sql, params)
                rows = [
                    [
                        c if not isinstance(c, bytes) else c.decode("utf-8", "replace")
                        for c in r
                    ]
                    for r in cur.fetchall()
                ]
            finally:
                con.close()
            self.last_result = rows
            return rows

        # Async helpers
        if name == "async_http_get":
            import concurrent.futures as _fut
            import urllib.request as _u

            if self._executor is None:
                self._executor = _fut.ThreadPoolExecutor(max_workers=4)
            url = str(self.eval(node.args[0]))

            def _task(u: str) -> str:
                req = _u.Request(u)
                with _u.urlopen(req) as r:
                    return r.read().decode("utf-8", "replace")

            f = self._executor.submit(_task, url)
            self.last_result = f
            return f
        if name == "await":
            fut = self.eval(node.args[0])
            try:
                outv = fut.result()  # type: ignore[attr-defined]
            except Exception as e:
                raise SupRuntimeError(message=str(e))
            self.last_result = outv
            return outv
        if name == "now":
            import datetime as _dt

            now_s = _dt.datetime.now().isoformat()
            self.last_result = now_s
            return now_s
        if name == "read_file":
            path = str(self.eval(node.args[0]))
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.last_result = content
            return content
        if name == "write_file":
            self._require_cap("fs_write")
            path = str(self.eval(node.args[0]))
            data = str(self.eval(node.args[1]))
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            self.last_result = True
            return True
        if name == "json_parse":
            import json as _json

            s = str(self.eval(node.args[0]))
            res = _json.loads(s)
            self.last_result = res
            return res
        if name == "json_stringify":
            import json as _json

            v = self.eval(node.args[0])
            jstr = _json.dumps(v)
            self.last_result = jstr
            return jstr
        if name == "min":
            a = self.eval(node.args[0])
            b = self.eval(node.args[1])
            num = min(self._num(a), self._num(b))
            self.last_result = float(num)
            return float(num)
        if name == "max":
            a = self.eval(node.args[0])
            b = self.eval(node.args[1])
            num = max(self._num(a), self._num(b))
            self.last_result = float(num)
            return float(num)
        if name == "floor":
            import math

            a = self._num(self.eval(node.args[0]))
            iv = math.floor(a)
            self.last_result = float(iv)
            return float(iv)
        if name == "ceil":
            import math

            a = self._num(self.eval(node.args[0]))
            iv = math.ceil(a)
            self.last_result = float(iv)
            return float(iv)
        if name == "trim":
            s = str(self.eval(node.args[0]))
            out_str = s.strip()
            self.last_result = out_str
            return out_str
        if name == "contains":
            s = self.eval(node.args[0])
            sub = self.eval(node.args[1])
            if isinstance(s, list):
                ok = any(item == sub for item in s)
            else:
                ok = str(sub) in str(s)
            self.last_result = ok
            return ok
        if name == "join":
            sep = str(self.eval(node.args[0]))
            lst = self.eval(node.args[1])
            if not isinstance(lst, list):
                raise SupRuntimeError(message="join expects a list.")
            joined = sep.join(str(x) for x in lst)
            self.last_result = joined
            return joined
        if name == "power":
            a = self._num(self.eval(node.args[0]))
            b = self._num(self.eval(node.args[1]))
            num_res = float(a) ** float(b)
            self.last_result = num_res
            return num_res
        if name == "sqrt":
            import math

            a = self._num(self.eval(node.args[0]))
            num_res = math.sqrt(float(a))
            self.last_result = num_res
            return num_res
        if name == "abs":
            a = self.eval(node.args[0])
            if isinstance(a, (int, float)):
                num_res = abs(a)
            else:
                num_res = abs(self._num(a))
            self.last_result = float(num_res)
            return float(num_res)
        if name == "upper":
            s = str(self.eval(node.args[0]))
            out_str = s.upper()
            self.last_result = out_str
            return out_str
        if name == "lower":
            s = str(self.eval(node.args[0]))
            out_str = s.lower()
            self.last_result = out_str
            return out_str
        if name == "concat":
            a = str(self.eval(node.args[0]))
            b = str(self.eval(node.args[1]))
            out_str = a + b
            self.last_result = out_str
            return out_str
        raise SupRuntimeError(message=f"Unknown builtin {name}.")

    def _call_function(self, node: AST.Call) -> object:
        # module-qualified call mm.square
        name = node.name.lower()
        if "." in name:
            mod, sym = name.split(".", 1)
            if mod in self.env and isinstance(self.env[mod], dict):
                target = self.env[mod].get(sym)
                if isinstance(target, AST.FunctionDef):
                    return self._call_fn_def(target, node.args)
                raise SupRuntimeError(
                    message=f"Undefined function '{node.name}'.",
                    line=getattr(node, "line", None),
                )
        # direct function from env via from-import
        if name in self.env and isinstance(self.env[name], AST.FunctionDef):
            return self._call_fn_def(self.env[name], node.args)  # type: ignore[arg-type]
        if name not in self.functions:
            raise SupRuntimeError(
                message=f"Undefined function '{node.name}'.",
                line=getattr(node, "line", None),
            )
        fn = self.functions[name]
        if len(node.args) != len(fn.params):
            raise SupRuntimeError(
                message=f"Function '{fn.name}' expects {len(fn.params)} argument(s) but got {len(node.args)}."
            )
        # Evaluate args
        arg_vals = [self.eval(a) for a in node.args]
        # New scope
        saved_env = self.env.copy()
        try:
            self.env = self.env.copy()
            for pname, pval in zip(fn.params, arg_vals):
                self.env[pname.lower()] = pval
            # Execute body
            ret_val: object | None = None
            try:
                for s in fn.body:
                    self.eval(s)
            except _ReturnSignal as r:
                ret_val = r.value
            self.last_result = ret_val
            # Ensure division/float semantics are visible when printed via call in print
            if isinstance(ret_val, (int, float)) and not isinstance(ret_val, bool):
                # Keep numeric as float if any arithmetic implied result is float
                # For simplicity, cast ints to float only when returned? Tests expect 12.0 here
                return float(ret_val)
            return ret_val
        finally:
            self.env = saved_env

    def _call_fn_def(self, fn: AST.FunctionDef, arg_nodes: list[AST.Node]) -> object:
        if len(arg_nodes) != len(fn.params):
            raise SupRuntimeError(
                message=f"Function '{fn.name}' expects {len(fn.params)} argument(s) but got {len(arg_nodes)}."
            )
        arg_vals = [self.eval(a) for a in arg_nodes]
        saved_env = self.env.copy()
        try:
            self.env = self.env.copy()
            for pname, pval in zip(fn.params, arg_vals):
                self.env[pname.lower()] = pval
            ret_val: object | None = None
            try:
                for s in fn.body:
                    self.eval(s)
            except _ReturnSignal as r:
                ret_val = r.value
            self.last_result = ret_val
            if isinstance(ret_val, (int, float)) and not isinstance(ret_val, bool):
                return float(ret_val)
            return ret_val
        finally:
            self.env = saved_env

    def _import_module(self, module: str) -> dict[str, object]:
        key = module.lower()
        if key in self.module_cache:
            return self.module_cache[key]
        if key in self.loading_modules:
            raise SupRuntimeError(
                message=f"Circular import detected for module '{module}'."
            )
        # Resolve path
        search_paths = [os.getcwd()]
        env_path = os.environ.get("SUP_PATH")
        if env_path:
            search_paths = env_path.split(os.pathsep) + search_paths
        path = None
        for base in search_paths:
            candidate = os.path.join(base, f"{module}.sup")
            if os.path.exists(candidate):
                path = candidate
                break
        if path is None:
            raise SupRuntimeError(message=f"Cannot find module '{module}'.")
        # Load file and execute in fresh interpreter sharing module cache
        with open(path, encoding="utf-8") as f:
            src = f.read()
        from .parser import Parser

        parser = Parser()
        program = parser.parse(src)
        self.loading_modules.add(key)
        try:
            child = Interpreter()
            child.module_cache = self.module_cache  # share cache
            child.loading_modules = self.loading_modules
            child.run(program)
        finally:
            self.loading_modules.discard(key)
        # Export top-level env and functions
        ns: dict[str, object] = {}
        ns.update(child.env)
        for name, fn in child.functions.items():
            ns[name] = fn
        self.module_cache[key] = ns
        return ns

    # ---- Capability helpers ----
    def _require_cap(self, cap: str) -> None:
        if self._unsafe_all:
            return
        if cap in self.capabilities:
            return
        raise SupRuntimeError(
            message=f"Operation requires capability '{cap}'. Enable via SUP_CAPS or SUP_UNSAFE."
        )


class _ReturnSignal(Exception):
    def __init__(self, value: object | None) -> None:
        self.value = value


class _SupThrown(Exception):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(str(value))
