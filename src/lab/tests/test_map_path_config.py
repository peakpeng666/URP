"""Map-only cloud checks may use a verified local asset copy, not a fake ROS install."""
import os
from pathlib import Path
import subprocess
import sys


def read_map_path(env):
    return subprocess.check_output(
        [sys.executable, '-c', 'from urp_lab.paths import ROS_MAPS; print(ROS_MAPS)'],
        cwd=Path(__file__).resolve().parents[1], env=env, text=True,
    ).strip()


def test_default_official_map_location():
    env = dict(os.environ)
    env.pop('URP_ROS_MAPS', None)
    assert read_map_path(env) == '/opt/ros/humble/share/turtlebot4_navigation/maps'


def test_explicit_map_copy_is_resolved(tmp_path):
    env = dict(os.environ, URP_ROS_MAPS=str(tmp_path / 'maps'))
    assert read_map_path(env) == str((tmp_path / 'maps').resolve())
