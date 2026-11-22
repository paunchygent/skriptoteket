from __future__ import annotations

from collections.abc import Iterable

from tinycss2 import ast as ast

def parse_stylesheet(
    input: str | Iterable[ast.Node],
    skip_comments: bool = False,
    skip_whitespace: bool = False,
) -> list[ast.Node]: ...
def parse_rule_list(
    input: str | Iterable[ast.Node],
    skip_comments: bool = False,
    skip_whitespace: bool = False,
) -> list[ast.Node]: ...
def parse_blocks_contents(
    input: str | Iterable[ast.Node],
    skip_comments: bool = False,
    skip_whitespace: bool = False,
) -> list[ast.Node]: ...
def serialize(nodes: Iterable[ast.Node]) -> str: ...
