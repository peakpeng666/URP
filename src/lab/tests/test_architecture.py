"""Anti-rot guards: keep the solver modules from silently growing back into monoliths.

Caps are set a little above the current refactored sizes; raising a cap is a deliberate
decision, not something that happens one feature at a time.
"""
import ast
from pathlib import Path

LAB = Path(__file__).resolve().parents[1] / 'urp_lab'

CAPS = {  # module → max lines
    'solvers/fleet.py': 950,
    'solvers/fleet_curvature.py': 250,
    'scenarios/validate.py': 460,
    'fieldworld.py': 520,
}

FUNCTION_CAPS = {  # (module, function) → max lines
    ('solvers/fleet.py', 'solve'): 210,
    ('solvers/fleet.py', 'check'): 175,
    ('solvers/fleet.py', 'metaheuristic'): 100,
}


def test_module_size_caps():
    for rel, cap in CAPS.items():
        path = LAB / rel
        assert path.is_file(), rel
        n = len(path.read_text(encoding='utf-8').splitlines())
        assert n <= cap, f'{rel} 已长到 {n} 行（上限 {cap}）：拆分或明确上调上限'


def test_function_size_caps():
    for (rel, fn), cap in FUNCTION_CAPS.items():
        tree = ast.parse((LAB / rel).read_text(encoding='utf-8'))
        sizes = {n.name: n.end_lineno - n.lineno for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert fn in sizes, f'{rel}:{fn} 不见了？'
        assert sizes[fn] <= cap, f'{rel}:{fn} 已长到 {sizes[fn]} 行（上限 {cap}）：提取子函数或明确上调上限'


def test_solver_layer_does_not_import_gateway():
    """Layering: solver modules must not depend on gateway/services state."""
    for path in (LAB / 'solvers').glob('*.py'):
        src = path.read_text(encoding='utf-8')
        for banned in ('from ..gateway', 'from ..services', 'import gateway', 'from ..store', 'from ..jobs'):
            assert banned not in src, f'{path.name} 引入了 {banned}（求解层不得依赖网关层）'
