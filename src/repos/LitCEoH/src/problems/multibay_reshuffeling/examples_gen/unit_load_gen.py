import sys
import os
sys.path.insert(0, os.path.abspath('./src'))

import numpy as np
from examples_gen.unit_load import UnitLoad

"""
TODO:
- Create virtual lanes
- Generate unit loads
- Place unit loads in lanes
- Calculate real fill level 
- Use unit load ids and store them into the initial bay state 
    - check that the unit loads are already arrived 
"""


class UnitLoadGenerator: 
    def __init__(self, tw_length: int, fill_level: float, seed: int): 
        """
        Creates a generator for unit loads with time windows

        Arguments:
        seed (int): seed for random generation
        fill_level (float): approximate fill level of the warehouse
        tw_length (int): approximate average length of the time windows
        """
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.fill_level = fill_level
        self.tw_length = tw_length
        

    def generate_bays_priorities(self, bays: list, height: int):
        """Generates random lanes and populates them with stacks"""

        # just for testing
        unit_loads = []
        unit_loads_dic = [
            {"id": 1, "retrieval_start": 1, "retrieval_end": 10, "arrival_start": 0, "arrival_end": 1},
            {"id": 2, "retrieval_start": 0, "retrieval_end": 10, "arrival_start": None, "arrival_end": None},
        ]
        for ul in unit_loads_dic: 
            unit_loads.append(UnitLoad(ul["id"], ul["retrieval_start"], ul["retrieval_end"], ul["arrival_start"], ul["arrival_end"]))

        return unit_loads
        