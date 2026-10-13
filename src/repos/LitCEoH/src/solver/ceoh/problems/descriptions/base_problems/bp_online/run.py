from .prompts import GetPrompts
import types
import warnings
import sys

from problems.bp_online.bp_online import BPonline

class BPONLINE_CONST():
    def __init__(self):
        self.prompts = GetPrompts()

        self.bp_online = BPonline()

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

                fitness = self.self.bp_online.evaluateGreedy(heuristic_module)

                return fitness
        except Exception as e:
            print("Error:", str(e))
            return None




