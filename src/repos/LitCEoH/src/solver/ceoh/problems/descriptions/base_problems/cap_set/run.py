import sys
import types
import warnings

from .prompts import GetPrompts

from problems.cap_set.cap_set import CapSet

DIMENSION_TO_SOLVE = 8


class CAP_SET_CONST:
    def __init__(self, code_string = None):
        """
        Initializes the reshuffle evaluation with a heuristic code string and instance count.

        Parameters:
        - code_string (str): Heuristic function as a string.
        """
        self.prompts = GetPrompts()

        self.cap_set = CapSet()

        if code_string != None:
            self.fitness = self.evaluate(code_string)

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
                fitness = self.cap_set.cap_set_evaluate(heuristic_module, DIMENSION_TO_SOLVE)

                print(f"--- Fitness --- {fitness}")

                return fitness

        except Exception as e:
             print("Error:", str(e))
             return None
