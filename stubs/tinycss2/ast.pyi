from __future__ import annotations

class Node:
    type: str
    source_line: int
    source_column: int

class Declaration(Node):
    name: str
    lower_name: str
    value: list[Node]
    important: bool

class QualifiedRule(Node):
    prelude: list[Node]
    content: list[Node]

class AtRule(Node):
    at_keyword: str
    lower_at_keyword: str
    prelude: list[Node]
    content: list[Node] | None
