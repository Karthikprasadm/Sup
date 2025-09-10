from __future__ import annotations

from . import ast as AST


def to_python(program: AST.Program) -> str:
    emitter = _PythonEmitter()
    return emitter.emit_program(program)


def to_python_with_map(
    program: AST.Program,
) -> tuple[str, list[int | None], list[int | None]]:
    emitter = _PythonEmitter()
    code = emitter.emit_program(program)
    return code, emitter.src_lines, emitter.src_cols


class _PythonEmitter:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.indent = 0
        self.in_function = 0
        self.src_lines: list[int | None] = []
        self.src_cols: list[int | None] = []
        self._current_src_line: int | None = None
        self._current_src_col: int | None = None

    def w(self, line: str = "") -> None:
        self.lines.append("    " * self.indent + line)
        self.src_lines.append(self._current_src_line)
        self.src_cols.append(self._current_src_col)

    def emit_program(self, program: AST.Program) -> str:
        self.w("# Transpiled from sup")
        self.w("from sys import stdout")
        self.w(
            "def _fmt(v):\n    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v"
        )
        # last_result mirrors interpreter semantics
        self.w("last_result = None")
        self.w()
        # Predeclare functions after scan
        for stmt in program.statements:
            if isinstance(stmt, AST.FunctionDef):
                self.emit_function(stmt)
        self.w()
        # Main body
        self.w("def __main__():")
        self.indent += 1
        # Declare globals up-front for any assigned names to avoid 'used prior to global' errors
        assigned = set()

        def collect_assigned(node: AST.Node) -> None:
            from . import ast as _AST

            if isinstance(node, _AST.Assignment):
                assigned.add(node.name)
            for attr in ("statements", "body", "else_body"):
                if hasattr(node, attr):
                    val = getattr(node, attr)
                    if isinstance(val, list):
                        for x in val:
                            if isinstance(x, _AST.Node):
                                collect_assigned(x)
                    elif isinstance(val, _AST.Node):
                        collect_assigned(val)

        for s in program.statements:
            collect_assigned(s)
        for name in sorted(assigned):
            self.w(f"global {name}")
        for stmt in program.statements:
            if not isinstance(stmt, AST.FunctionDef):
                self._current_src_line = getattr(stmt, "line", None)
                self._current_src_col = getattr(stmt, "column", None)
                self.emit_stmt(stmt)
        self.indent -= 1
        self.w()
        # Execute when run as a script or via runpy.run_path (which sets __spec__ to None)
        self.w("if __name__ == '__main__' or globals().get('__spec__') is None:")
        self.indent += 1
        self.w("__main__()")
        self.indent -= 1
        return "\n".join(self.lines) + "\n"

    def emit_function(self, fn: AST.FunctionDef) -> None:
        params = ", ".join(fn.params)
        self._current_src_line = getattr(fn, "line", None)
        self._current_src_col = getattr(fn, "column", None)
        self.w(f"def {fn.name}({params}):")
        self.indent += 1
        self.w("global last_result")
        self.in_function += 1
        for s in fn.body:
            self._current_src_line = getattr(s, "line", None)
            self._current_src_col = getattr(s, "column", None)
            self.emit_stmt(s)
        self.in_function -= 1
        self.indent -= 1
        self.w()

    def emit_stmt(self, node: AST.Node) -> None:
        if isinstance(node, AST.Assignment):
            value = self.emit_expr(node.expr)
            self.w(f"{node.name} = {value}")
            self.w(f"last_result = {node.name}")
            return
        if isinstance(node, AST.Print):
            if node.expr is None:
                self.w("print(last_result)")
            else:
                self.w(f"print({self.emit_expr(node.expr)})")
            return
        if isinstance(node, AST.If):
            cond = node.cond if node.cond is not None else AST.Compare(op=node.op, left=node.left, right=node.right)  # type: ignore[arg-type]
            self.w(f"if {self.emit_expr(cond)}:")
            self.indent += 1
            for s in node.body:
                self._current_src_line = getattr(s, "line", None)
                self._current_src_col = getattr(s, "column", None)
                self.emit_stmt(s)
            self.indent -= 1
            if node.else_body is not None:
                self.w("else:")
                self.indent += 1
                for s in node.else_body:
                    self._current_src_line = getattr(s, "line", None)
                    self._current_src_col = getattr(s, "column", None)
                    self.emit_stmt(s)
                self.indent -= 1
            return
        if isinstance(node, AST.While):
            self.w(f"while {self.emit_expr(node.cond)}:")
            self.indent += 1
            for s in node.body:
                self._current_src_line = getattr(s, "line", None)
                self._current_src_col = getattr(s, "column", None)
                self.emit_stmt(s)
            self.indent -= 1
            return
        if isinstance(node, AST.ForEach):
            self.w(f"for {node.var} in {self.emit_expr(node.iterable)}:")
            self.indent += 1
            for s in node.body:
                self._current_src_line = getattr(s, "line", None)
                self._current_src_col = getattr(s, "column", None)
                self.emit_stmt(s)
            self.indent -= 1
            return
        if isinstance(node, AST.Repeat):
            self.w(f"for _ in range(int({self.emit_expr(node.count_expr)})):")
            self.indent += 1
            for s in node.body:
                self._current_src_line = getattr(s, "line", None)
                self._current_src_col = getattr(s, "column", None)
                self.emit_stmt(s)
            self.indent -= 1
            return
        if isinstance(node, AST.ExprStmt):
            self.w(f"last_result = {self.emit_expr(node.expr)}")
            return
        if isinstance(node, AST.Return):
            if node.expr is None:
                self.w("return None")
            else:
                self.w(f"return _fmt({self.emit_expr(node.expr)})")
            return
        if isinstance(node, AST.FunctionDef):
            # already emitted
            return
        if isinstance(node, AST.TryCatch):
            self.w("try:")
            self.indent += 1
            for s in node.body:
                self.emit_stmt(s)
            self.indent -= 1
            if node.catch_body is not None:
                name = node.catch_name or "_e"
                self.w(f"except Exception as {name}:")
                self.indent += 1
                for s in node.catch_body:
                    self.emit_stmt(s)
                self.indent -= 1
            if node.finally_body is not None:
                self.w("finally:")
                self.indent += 1
                for s in node.finally_body:
                    self.emit_stmt(s)
                self.indent -= 1
            return
        if isinstance(node, AST.Throw):
            self.w(f"raise Exception({self.emit_expr(node.value)})")
            return
        if isinstance(node, AST.Import):
            alias = f" as {node.alias}" if node.alias else ""
            self.w(f"import {node.module}{alias}")
            return
        if isinstance(node, AST.FromImport):
            parts = []
            # Avoid shadowing earlier 'alias' variable with Optional[str]
            for name, alias_name in node.names:
                parts.append(f"{name} as {alias_name}" if alias_name else name)
            self.w(f"from {node.module} import {', '.join(parts)}")
            return
        raise NotImplementedError(f"Unsupported statement {type(node).__name__}")

    def emit_expr(self, node: AST.Node) -> str:
        if isinstance(node, AST.Number):
            return str(node.value)
        if isinstance(node, AST.String):
            return repr(node.value)
        if isinstance(node, AST.Identifier):
            return node.name
        if isinstance(node, AST.Binary):
            return (
                f"({self.emit_expr(node.left)} {node.op} {self.emit_expr(node.right)})"
            )
        if isinstance(node, AST.Call):
            args = ", ".join(self.emit_expr(a) for a in node.args)
            return f"{node.name}({args})"
        if isinstance(node, AST.MakeList):
            return f"[{', '.join(self.emit_expr(it) for it in node.items)}]"
        if isinstance(node, AST.MakeMap):
            return "{}"
        if isinstance(node, AST.Push):
            return f"{self.emit_expr(node.target)}.append({self.emit_expr(node.item)})"
        if isinstance(node, AST.Pop):
            return f"{self.emit_expr(node.target)}.pop()"
        if isinstance(node, AST.GetKey):
            # .get may return Optional; cast to str for emitted Python simplicity
            return f"{self.emit_expr(node.target)}.get({self.emit_expr(node.key)})"
        if isinstance(node, AST.SetKey):
            return f"{self.emit_expr(node.target)}[{self.emit_expr(node.key)}] = {self.emit_expr(node.value)}"
        if isinstance(node, AST.DeleteKey):
            return (
                f"{self.emit_expr(node.target)}.pop({self.emit_expr(node.key)}, None)"
            )
        if isinstance(node, AST.Length):
            return f"len({self.emit_expr(node.target)})"
        if isinstance(node, AST.BoolBinary):
            op = "and" if node.op == "and" else "or"
            return f"({self.emit_expr(node.left)} {op} {self.emit_expr(node.right)})"
        if isinstance(node, AST.NotOp):
            return f"(not {self.emit_expr(node.expr)})"
        if isinstance(node, AST.Compare):
            return (
                f"({self.emit_expr(node.left)} {node.op} {self.emit_expr(node.right)})"
            )
        if isinstance(node, AST.BuiltinCall):
            mapping = {
                "power": lambda args: f"({args[0]}) ** ({args[1]})",
                "sqrt": lambda args: f"({args[0]}) ** 0.5",
                "abs": lambda args: f"abs({args[0]})",
                "upper": lambda args: f"str({args[0]}).upper()",
                "lower": lambda args: f"str({args[0]}).lower()",
                "concat": lambda args: f"str({args[0]}) + str({args[1]})",
            }
            arg_vals = [self.emit_expr(a) for a in node.args]
            if node.name in mapping:
                return mapping[node.name](arg_vals)
            raise NotImplementedError(f"Unsupported builtin {node.name}")
        raise NotImplementedError(f"Unsupported expression {type(node).__name__}")


_VLQ_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _to_vlq_signed(value: int) -> int:
    return (value << 1) ^ (value >> 31)


def _encode_vlq(value: int) -> str:
    vlq = _to_vlq_signed(value)
    out = ""
    while True:
        digit = vlq & 31
        vlq >>= 5
        if vlq:
            digit |= 32
        out += _VLQ_CHARS[digit]
        if not vlq:
            break
    return out


def build_sourcemap_mappings(
    gen_src_lines: list[int | None], gen_src_cols: list[int | None]
) -> str:
    # Standard V3: each segment = [generatedColumn, sourceIndex, originalLine, originalColumn]
    mappings: list[str] = []
    last_gen_col = 0
    last_src_idx = 0
    last_orig_line = 0
    last_orig_col = 0
    for src_line, src_col in zip(gen_src_lines, gen_src_cols):
        if src_line is None:
            mappings.append("")
            last_gen_col = 0
            continue
        seg = (
            f"{_encode_vlq(0 - last_gen_col)}"  # reset to start of line
            f"{_encode_vlq(0 - last_src_idx)}"  # single source
            f"{_encode_vlq(max(0, (src_line - 1) - last_orig_line))}"
            f"{_encode_vlq(max(0, (src_col or 0) - last_orig_col))}"
        )
        mappings.append(seg)
        last_gen_col = 0
        last_src_idx = 0
        last_orig_line = src_line - 1
        last_orig_col = src_col or 0
    return ";".join(mappings)
