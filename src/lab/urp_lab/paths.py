"""Repository locations shared by the gateway, worker and core modules."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LAB = REPO / 'src' / 'lab'
RUNTIME = Path(os.environ['URP_LAB_RUNTIME']).resolve() if os.environ.get('URP_LAB_RUNTIME') else LAB / 'runtime'
RESEARCH_SRC = REPO / 'src' / 'research' / 'src'
FRONTEND = REPO / 'src' / 'frontend'
FRONTEND_DIST = FRONTEND / 'dist'
FRONTEND_ROUTING = FRONTEND / 'core' / 'routing'
DEPLOYMENT = REPO / 'setup' / '2026-10-15' / 'deployment'
ROS_MAPS = Path('/opt/ros/humble/share/turtlebot4_navigation/maps')
USER_SCENARIOS = RUNTIME / 'scenarios'
CVRP_SELECTION_DATA = REPO / 'data' / 'research' / 'cvrp-selection-crc'


def ensure_research_path() -> Path:
    """Make the frozen research package importable (never modified, only imported)."""
    path = str(RESEARCH_SRC)
    if path not in sys.path:
        sys.path.insert(0, path)
    return RESEARCH_SRC


def rel(path: Path | str) -> str:
    """Repository-relative path for labels; absolute paths outside the repo are kept."""
    p = Path(path)
    try:
        return p.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(p)

LOGS = RUNTIME / 'logs'
SIM = RUNTIME / 'sim'
EXPORTS = RUNTIME / 'exports'
