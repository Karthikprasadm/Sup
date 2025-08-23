from __future__ import annotations

from typing import List

from . import ast as AST


def to_python(program: AST.Program) -> str:
    emitter = _PythonEmitter()
    return emitter.emit_program(program)


class _PythonEmitter:
    def __init__(self) -> None:
        self.lines: List[str] = []
        self.indent = 0
        self.in_function = 0

    def w(self, line: str = "") -> None:
        self.lines.append("    " * self.indent + line)

    def emit_program(self, program: AST.Program) -> str:
        self.w("# Transpiled from sup")
        self.w("from sys import stdout")
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
        for stmt in program.statements:
            if not isinstance(stmt, AST.FunctionDef):
                self.emit_stmt(stmt)
        self.indent -= 1
        self.w()
        self.w("if __name__ == '__main__':")
        self.indent += 1
        self.w("__main__()")
        self.indent -= 1
        return "\n".join(self.lines) + "\n"

    def emit_function(self, fn: AST.FunctionDef) -> None:
        params = ", ".join(fn.params)
        self.w(f"def {fn.name}({params}):")
        self.indent += 1
        self.w("global last_result")
        self.in_function += 1
        for s in fn.body:
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
                self.emit_stmt(s)
            self.indent -= 1
            if node.else_body is not None:
                self.w("else:")
                self.indent += 1
                for s in node.else_body:
                    self.emit_stmt(s)
                self.indent -= 1
            return
        if isinstance(node, AST.While):
            self.w(f"while {self.emit_expr(node.cond)}:")
            self.indent += 1
            for s in node.body:
                self.emit_stmt(s)
            self.indent -= 1
            return
        if isinstance(node, AST.ForEach):
            self.w(f"for {node.var} in {self.emit_expr(node.iterable)}:")
            self.indent += 1
            for s in node.body:
                self.emit_stmt(s)
            self.indent -= 1
            return
        if isinstance(node, AST.Repeat):
            self.w(f"for _ in range(int({self.emit_expr(node.count_expr)})):")
            self.indent += 1
            for s in node.body:
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
                self.w(f"return {self.emit_expr(node.expr)}")
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
            for name, alias in node.names:
                parts.append(f"{name} as {alias}" if alias else name)
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
            return f"({self.emit_expr(node.left)} {node.op} {self.emit_expr(node.right)})"
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
            return f"{self.emit_expr(node.target)}.get({self.emit_expr(node.key)})"
        if isinstance(node, AST.SetKey):
            return f"{self.emit_expr(node.target)}[{self.emit_expr(node.key)}] = {self.emit_expr(node.value)}"
        if isinstance(node, AST.DeleteKey):
            return f"{self.emit_expr(node.target)}.pop({self.emit_expr(node.key)}, None)"
        if isinstance(node, AST.Length):
            return f"len({self.emit_expr(node.target)})"
        if isinstance(node, AST.BoolBinary):
            op = 'and' if node.op == 'and' else 'or'
            return f"({self.emit_expr(node.left)} {op} {self.emit_expr(node.right)})"
        if isinstance(node, AST.NotOp):
            return f"(not {self.emit_expr(node.expr)})"
        if isinstance(node, AST.Compare):
            return f"({self.emit_expr(node.left)} {node.op} {self.emit_expr(node.right)})"
        if isinstance(node, AST.BuiltinCall):
            mapping = {
                "power": lambda args: f"({args[0]}) ** ({args[1]})",
                "sqrt": lambda args: f"({args[0]}) ** 0.5",
                "abs": lambda args: f"abs({args[0]})",
                "upper": lambda args: f"str({args[0]}).upper()",
                "lower": lambda args: f"str({args[0]}).lower()",
                "concat": lambda args: f"str({args[0]}) + str({args[1]})",
            }
            args = [self.emit_expr(a) for a in node.args]
            if node.name in mapping:
                return mapping[node.name](args)
            raise NotImplementedError(f"Unsupported builtin {node.name}")
        raise NotImplementedError(f"Unsupported expression {type(node).__name__}")


