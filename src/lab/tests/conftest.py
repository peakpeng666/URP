"""Keep optional map tests explicit; CI can require the real assets."""
import os

import pytest

from urp_lab import paths


def pytest_addoption(parser):
    parser.addoption('--require-maps', action='store_true', help='Fail when a marked official map is missing')


def pytest_configure(config):
    config.addinivalue_line('markers', 'requires_maps(*worlds): needs official TurtleBot4 occupancy maps')


def pytest_runtest_setup(item):
    marker = item.get_closest_marker('requires_maps')
    if marker is None:
        return
    missing = [world for world in marker.args if not (paths.ROS_MAPS / f'{world}.yaml').is_file()]
    if missing:
        reason = f"Missing official maps {', '.join(missing)} in {paths.ROS_MAPS}; run tools/fetch_ros_maps.py"
        if item.config.getoption('--require-maps') or os.environ.get('URP_ROS_MAPS'):
            pytest.fail(reason, pytrace=False)
        pytest.skip(reason)
