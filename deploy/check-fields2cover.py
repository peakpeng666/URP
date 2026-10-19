#!/usr/bin/env python3
"""Run with lab Python; verify F2C bytes and coexistence with the other native solvers."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'src/lab/vendor/fields2cover-manifest.json').read_text())
    try:
        # The workbench can load these libraries before F2C in the same process.
        # Separate import probes cannot detect conflicting native dependencies.
        from ortools.constraint_solver import pywrapcp
        import pyvrp
        from ompl import base as ob, geometric as og
        ortools_solver = pywrapcp.Solver('f2c-combined-load-check')
        pyvrp_model = pyvrp.Model()
        pyvrp_model.add_depot(pyvrp_model.add_location(0, 0))
        space = ob.RealVectorStateSpace(2)
        bounds = ob.RealVectorBounds(2)
        bounds.setLow(0)
        bounds.setHigh(1)
        space.setBounds(bounds)
        ompl_setup = og.SimpleSetup(space)
        import fields2cover as f2c
        binary = Path(f2c.__file__).parent / '_fields2cover_python.so'
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        if digest != manifest['binary_sha256']:
            raise ValueError('installed extension SHA256 differs from the accepted manifest')
        if importlib.metadata.version('fields2cover') != manifest['version']:
            raise ValueError('installed Fields2Cover version differs from the manifest')
        point = f2c.Point(1.0, 2.0)
        if (point.getX(), point.getY()) != (1.0, 2.0):
            raise ValueError('native Point roundtrip failed')
    except (ImportError, OSError, ValueError, AttributeError) as exc:
        print(f'Combined native solver/F2C load check failed: {exc}. The pinned wheel needs Ubuntu 22.04 amd64, '
              'CPython 3.12 and deploy/fields2cover-packages.txt libraries.', file=sys.stderr)
        return 1
    print(json.dumps(dict(passed=True, scope='same-process OR-Tools/PyVRP/OMPL/F2C load and Point smoke only',
                         version=manifest['version'], binary_sha256=digest)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
