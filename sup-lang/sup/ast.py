from __future__ import annotations

from dataclasses import dataclass


# AST Node base
class Node:
    line: int | None = None


@dataclass
class Program(Node):
    statements: list[Node]


@dataclass
class Assignment(Node):
    name: str
    expr: Node


@dataclass
class Print(Node):
    expr: Node | None  # None means print last_result


@dataclass
class Ask(Node):
    name: str


@dataclass
class If(Node):
    # Back-compat fields for simple comparisons
    left: Node | None = None
    op: str | None = None  # one of '>', '<', '==', '!=', '>=', '<='
    right: Node | None = None
    # General condition node when using boolean expressions
    cond: Node | None = None
    body: list[Node] = None  # type: ignore[assignment]
    else_body: list[Node] | None = None


@dataclass
class Repeat(Node):
    count_expr: Node
    body: list[Node]


@dataclass
class ExprStmt(Node):
    expr: Node


@dataclass
class Binary(Node):
    op: str  # one of '+', '-', '*', '/'
    left: Node
    right: Node


@dataclass
class Identifier(Node):
    name: str


@dataclass
class Number(Node):
    value: int | float


@dataclass
class String(Node):
    value: str


@dataclass
class FunctionDef(Node):
    name: str
    params: list[str]
    body: list[Node]


@dataclass
class Return(Node):
    expr: Node | None


@dataclass
class Call(Node):
    name: str
    args: list[Node]


# Collections and stdlib


@dataclass
class MakeList(Node):
    items: list[Node]


@dataclass
class MakeMap(Node):
    # Empty map creation for MVP
    pass


@dataclass
class Push(Node):
    item: Node
    target: Node


@dataclass
class Pop(Node):
    target: Node


@dataclass
class GetKey(Node):
    key: Node
    target: Node


@dataclass
class SetKey(Node):
    key: Node
    value: Node
    target: Node


@dataclass
class DeleteKey(Node):
    key: Node
    target: Node


@dataclass
class Length(Node):
    target: Node


@dataclass
class Index(Node):
    target: Node
    index: Node


@dataclass
class BuiltinCall(Node):
    name: str
    args: list[Node]


@dataclass
class While(Node):
    cond: Node
    body: list[Node]


@dataclass
class ForEach(Node):
    var: str
    iterable: Node
    body: list[Node]


@dataclass
class BoolBinary(Node):
    op: str  # 'and' | 'or'
    left: Node
    right: Node


@dataclass
class NotOp(Node):
    expr: Node


@dataclass
class Compare(Node):
    op: str  # one of '==', '!=', '<', '>', '<=', '>='
    left: Node
    right: Node


@dataclass
class TryCatch(Node):
    body: list[Node]
    catch_name: str | None
    catch_body: list[Node] | None
    finally_body: list[Node] | None


@dataclass
class Throw(Node):
    value: Node


@dataclass
class Import(Node):
    module: str
    alias: str | None


@dataclass
class FromImport(Node):
    module: str
    names: list[tuple[str, str | None]]
