import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))

import unittest

code_string = """
def select_next_move(warehouse_states):
    scores = []
    for state in warehouse_states:
        score = 0
        reshuffles = 0
        accessible_high_priority = 0
        for aisle_index, aisle in enumerate(state):
            for level_index, level in enumerate(aisle):
                if level != 0:
                    priority = level
                    blocking_factor = sum([
                        abs(level - upper_level) 
                        for upper_level in aisle 
                        if upper_level > priority
                    ])
                    score += priority - (blocking_factor * (level_index + 1)) 
                    if blocking_factor == 0:
                        accessible_high_priority += priority
                    if blocking_factor > 0:
                        reshuffles += (level_index + 1) * (aisle_index + 1)
        scores.append(score + accessible_high_priority - reshuffles)
    return scores
"""


class TestMR(unittest.TestCase):

    def setUp(self):

        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        base_path = f"{self.dir_path}/../.."

        os.environ["BASE_PATH"]  = base_path

        os.environ["INSTANCES_PATH"] = f"{base_path}/data/mr_examples"
        os.environ["OUTPUT_PATH"] = f"{base_path}/ceoh_results"

        self.eoh_experiment_file = "exp_bay5_wh_2_fill_0.6.json"

    def test_run(self):
        # TODO: Enable test files
        # reshuffle_const = MULTIBAY_RESHUFFLECONST(self.eoh_experiment_file, code_string)
        # self.assertGreater(reshuffle_const.fitness[0], 0)
        pass


if __name__ == '__main__':
    unittest.main()
