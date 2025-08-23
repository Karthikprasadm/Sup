from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union


# AST Node base
class Node:
    line: Optional[int] = None


@dataclass
class Program(Node):
    statements: List[Node]


@dataclass
class Assignment(Node):
    name: str
    expr: Node


@dataclass
class Print(Node):
    expr: Optional[Node]  # None means print last_result


@dataclass
class Ask(Node):
    name: str


@dataclass
class If(Node):
    # Back-compat fields for simple comparisons
    left: Optional[Node] = None
    op: Optional[str] = None  # one of '>', '<', '==', '!=', '>=', '<='
    right: Optional[Node] = None
    # General condition node when using boolean expressions
    cond: Optional[Node] = None
    body: List[Node] = None  # type: ignore[assignment]
    else_body: Optional[List[Node]] = None


@dataclass
class Repeat(Node):
    count_expr: Node
    body: List[Node]


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
    value: Union[int, float]


@dataclass
class String(Node):
    value: str


@dataclass
class FunctionDef(Node):
    name: str
    params: List[str]
    body: List[Node]


@dataclass
class Return(Node):
    expr: Optional[Node]


@dataclass
class Call(Node):
    name: str
    args: List[Node]


# Collections and stdlib

@dataclass
class MakeList(Node):
    items: List[Node]


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
    args: List[Node]


@dataclass
class While(Node):
    cond: Node
    body: List[Node]


@dataclass
class ForEach(Node):
    var: str
    iterable: Node
    body: List[Node]


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
    body: List[Node]
    catch_name: Optional[str]
    catch_body: Optional[List[Node]]
    finally_body: Optional[List[Node]]


@dataclass
class Throw(Node):
    value: Node


@dataclass
class Import(Node):
    module: str
    alias: Optional[str]


@dataclass
class FromImport(Node):
    module: str
    names: List[tuple[str, Optional[str]]]

