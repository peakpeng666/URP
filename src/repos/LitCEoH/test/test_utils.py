import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

import unittest
import numpy as np
from problems.multibay_reshuffeling.bay.access_bay import AccessBay
from problems.multibay_reshuffeling.mr_util.access_util import (next_in_direction)

class TestUtil(unittest.TestCase):

    def setUp(self):
        state = np.zeros((3, 3, 3))
        self.bay = AccessBay(0, 0, state, [])

    def test_next_inv_y(self):
        with self.assertRaises(ValueError):
            next_in_direction(self.bay, (-1, 1), 'north')

    def test_next_inv_x(self):
        with self.assertRaises(ValueError):
            next_in_direction(self.bay, (1, -1), 'north')

    def test_next_north(self):
        self.assertEqual(next_in_direction(self.bay, (0, 0), 'north'), (1, 0))

    def test_next_west(self):
        self.assertEqual(next_in_direction(self.bay, (0, 0), 'west'), (0, 1))


if __name__ == '__main__':
    unittest.main()
