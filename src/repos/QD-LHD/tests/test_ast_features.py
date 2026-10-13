"""Unit tests for :mod:`qd_lhd.ast_features`."""

from __future__ import annotations

import numpy as np
import pytest

from qd_lhd.ast_features import AST_FEATURE_NAMES, extract_ast_features

SIMPLE = """
def heuristic(inst):
    x = 1 + 2
    return x
"""

NESTED_LOOPS = """
def heuristic(inst):
    total = 0
    for i in range(inst.n):
        for j in range(i, inst.n):
            if i < j:
                total += inst.dist(i, j)
    return total
"""

RECURSIVE_SORT = """
def heuristic(inst):
    nodes = sorted(range(inst.n), key=lambda k: inst.dist(0, k))
    def visit(i):
        if i >= len(nodes):
            return []
        return [nodes[i]] + visit(i + 1)
    return visit(0)
"""


def test_feature_vector_has_expected_shape_and_type():
    vec = extract_ast_features(SIMPLE)
    assert vec.shape == (11,)
    assert vec.dtype == np.float32
    assert len(AST_FEATURE_NAMES) == 11


def test_simple_heuristic_has_no_loops_branches_or_recursion():
    vec = extract_ast_features(SIMPLE)
    names = dict(zip(AST_FEATURE_NAMES, vec))
    assert names["num_loops"] == 0
    assert names["num_branches"] == 0
    assert names["has_recursion"] == 0
    assert names["has_sorting"] == 0
    assert names["num_arith"] >= 1  # 1 + 2


def test_nested_loops_capture_structure():
    vec = extract_ast_features(NESTED_LOOPS)
    names = dict(zip(AST_FEATURE_NAMES, vec))
    assert names["num_loops"] == 2
    assert names["loop_nesting"] == 2
    assert names["num_branches"] == 1
    assert names["num_compare"] >= 1


def test_recursion_and_sorting_detected():
    vec = extract_ast_features(RECURSIVE_SORT)
    names = dict(zip(AST_FEATURE_NAMES, vec))
    assert names["has_recursion"] == 1
    assert names["has_sorting"] == 1
    assert names["num_ds_types"] >= 1


def test_syntax_error_propagates():
    with pytest.raises(SyntaxError):
        extract_ast_features("def broken(:")
