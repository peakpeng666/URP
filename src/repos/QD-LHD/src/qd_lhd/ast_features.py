"""AST-based feature extraction for heuristic programs.

Implements the 11 features of Table 2 in the manuscript: structural, control-flow,
operation-count, and algorithmic indicators computed from a heuristic's Python source.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

import numpy as np

AST_FEATURE_NAMES: tuple[str, ...] = (
    "ast_depth",
    "num_nodes",
    "code_lines",
    "num_loops",
    "loop_nesting",
    "num_branches",
    "num_arith",
    "num_compare",
    "has_recursion",
    "has_sorting",
    "num_ds_types",
)

_SORT_CALLS = {"sort", "sorted", "heapify", "heappush", "heappop", "argsort"}
_ARITH_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_DS_TYPES = {"list", "dict", "set", "tuple", "deque", "heap", "heapq", "defaultdict"}


@dataclass(frozen=True, slots=True)
class _Stats:
    depth: int
    node_count: int
    loop_nesting: int


def _compute_stats(tree: ast.AST) -> _Stats:
    depth = 0
    node_count = 0
    loop_nesting = 0

    def walk(node: ast.AST, cur_depth: int, cur_loop_depth: int) -> None:
        nonlocal depth, node_count, loop_nesting
        node_count += 1
        depth = max(depth, cur_depth)
        loop_nesting = max(loop_nesting, cur_loop_depth)
        new_loop_depth = cur_loop_depth + 1 if isinstance(node, (ast.For, ast.While)) else cur_loop_depth
        for child in ast.iter_child_nodes(node):
            walk(child, cur_depth + 1, new_loop_depth)

    walk(tree, 0, 0)
    return _Stats(depth=depth, node_count=node_count, loop_nesting=loop_nesting)


def _function_calls_itself(tree: ast.AST) -> bool:
    func_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_names.add(node.name)
    if not func_names:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in func_names:
                return True
    return False


def _uses_sorting(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in _SORT_CALLS:
                return True
            if isinstance(func, ast.Name) and func.id in _SORT_CALLS:
                return True
    return False


def _distinct_ds_types(tree: ast.AST) -> int:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            found.add("list")
        elif isinstance(node, ast.Dict):
            found.add("dict")
        elif isinstance(node, ast.Set):
            found.add("set")
        elif isinstance(node, ast.Tuple):
            found.add("tuple")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name in _DS_TYPES:
                found.add(name)
    return len(found)


def extract_ast_features(source: str) -> np.ndarray:
    """Parse ``source`` and return the 11-dimensional AST feature vector.

    Parameters
    ----------
    source: str
        Python source code of a heuristic program.

    Returns
    -------
    numpy.ndarray, shape (11,), dtype=float32
        Feature vector in the order listed in :data:`AST_FEATURE_NAMES`.

    Raises
    ------
    SyntaxError
        If ``source`` is not valid Python.
    """
    tree = ast.parse(source)
    stats = _compute_stats(tree)
    num_loops = sum(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree))
    num_branches = sum(isinstance(n, (ast.If, ast.IfExp, ast.Match)) for n in ast.walk(tree))
    num_arith = sum(isinstance(n, ast.BinOp) and isinstance(n.op, _ARITH_OPS) for n in ast.walk(tree))
    num_compare = sum(isinstance(n, ast.Compare) for n in ast.walk(tree))
    code_lines = sum(1 for line in source.splitlines() if line.strip() and not line.strip().startswith("#"))

    return np.array(
        [
            float(stats.depth),
            float(stats.node_count),
            float(code_lines),
            float(num_loops),
            float(stats.loop_nesting),
            float(num_branches),
            float(num_arith),
            float(num_compare),
            float(_function_calls_itself(tree)),
            float(_uses_sorting(tree)),
            float(_distinct_ds_types(tree)),
        ],
        dtype=np.float32,
    )
