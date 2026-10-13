import sys
import types
import warnings
from .prompts import GetPrompts
from problems.tsp_greedy.get_instance import GetData
from problems.tsp_greedy.tsp import TSP

class TSPCONST():

    def __init__(self):

        self.prompts = GetPrompts()

        getData = GetData(self.n_instance, self.problem_size)
        instance_data = getData.generate_instances()

        n_instance = 8
        problem_size = 50

        self.tsp = TSP(instance_data, n_instance, problem_size)


    def evaluate(self, code_string):
        try:
            # Suppress warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # Create a new module object
                heuristic_module = types.ModuleType("heuristic_module")
                
                # Execute the code string in the new module's namespace
                exec(code_string, heuristic_module.__dict__)

                # Add the module to sys.modules so it can be imported
                sys.modules[heuristic_module.__name__] = heuristic_module

                # Now you can use the module as you would any other
                fitness = self.tsp.greedy(heuristic_module)
                return fitness
        except Exception as e:
            print("Error:", str(e))
            return None
