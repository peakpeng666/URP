import sys

sys.path.insert(0, '../src')

import unittest
import numpy as np
from problems.multibay_reshuffeling.bay.virtual_lane import VirtualLane


class TestVirtualLanes(unittest.TestCase):

    def setUp(self):
        pass

    def test_empty_lane(self):
        stacks = np.zeros(5)
        lane = VirtualLane()
        lane.stacks = stacks
        self.assertTrue(lane.has_slots())
        self.assertFalse(lane.has_loads())

    def test_full_lane(self):
        stacks = np.ones(5)
        lane = VirtualLane()
        lane.stacks = stacks
        self.assertFalse(lane.has_slots())
        self.assertTrue(lane.has_loads())

    def test_semi_full_lane(self):
        stacks = np.zeros(5)
        stacks[-1] = 1
        lane = VirtualLane()
        lane.stacks = stacks
        self.assertTrue(lane.has_slots())
        self.assertTrue(lane.has_loads())


if __name__ == '__main__':
    unittest.main()
