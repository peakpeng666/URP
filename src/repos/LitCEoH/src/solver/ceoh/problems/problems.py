


class Probs():
    def __init__(self,paras):

        if not isinstance(paras.problem, str):
            self.prob = paras.problem
            print("- Prob local loaded ")
        elif paras.problem == "tsp_construct":
            from solver.ceoh.problems.descriptions.base_problems.tsp_greedy import run
            self.prob = run.TSPCONST()
            print("- Prob "+paras.problem+" loaded ")
        elif paras.problem == "bp_online":
            from solver.ceoh.problems.descriptions.base_problems.bp_online import run
            self.prob = run.BPONLINE_CONST()
            print("- Prob "+paras.problem+" loaded ")
        elif paras.problem == "cap_set":

            if paras.ec_use_example:
                raise Exception("CAP SET CANNOT BE EXCECUTED WITH EXAMPLE!")

            from solver.ceoh.problems.descriptions.base_problems.cap_set import run
            self.prob = run.CAP_SET_CONST()
            print("- Prob " + paras.problem + " loaded ")
        elif paras.problem == "multibay_reshuffle":
            from solver.ceoh.problems.descriptions.upmp.multibay_reshuffeling import run
            self.prob = run.MULTIBAY_RESHUFFLECONST(paras.eoh_experiment_file)
            print("- Prob " + paras.problem + " loaded ")
        elif paras.problem == "multibay_reshuffle_travel_time":
            from solver.ceoh.problems.descriptions.upmp.multibay_reshuffle_travel_time import run
            self.prob = run.MULTIBAY_RESHUFFLE_TRAVEL_TIME_CONST(paras.eoh_experiment_file)
            print("- Prob " + paras.problem + " loaded ")
        elif paras.problem == "multibay_reshuffle_astar":
            from solver.ceoh.problems.descriptions.upmp.multibay_reshuffle_astar import run
            self.prob = run.MULTIBAY_RESHUFFLECONST_ASTAR(paras.eoh_experiment_file)
            print("- Prob " + paras.problem + " loaded ")

        elif paras.problem == "cvrp":
            from solver.ceoh.problems.descriptions.vrp.cvrp import run
            self.prob = run.CVRP_CONSTANT(code_string=None, paras=paras)
            print("- Prob " + paras.problem + " loaded ")
        elif paras.problem == "vrptw":
            from .optimization.vrptw import run
            self.prob = run.VRPTW_CONSTANT(code_string=None, paras=paras)
            print("- Prob " + paras.problem + " loaded ")
        elif paras.problem == "ovrpmbltw":
            from .optimization.ovrpmbltw import run
            self.prob = run.OVRPMBLTW_CONSTANT(code_string=None, paras=paras)
            print("- Prob " + paras.problem + " loaded ")

        elif paras.problem == "puzzle_greedy":
            from solver.ceoh.problems.descriptions.puzzle.puzzle_greedy import run
            self.prob = run.PUZZLE_GREEDY_CONST(code_string=None, paras=paras)
            print("- Prob " + paras.problem + " loaded ")
        elif paras.problem == "puzzle_astar_korf":
            from solver.ceoh.problems.descriptions.puzzle.puzzle_astar_korf import run
            self.prob = run.PUZZLE_ASTAR(code_string=None, paras=paras)
            print("- Prob " + paras.problem + " loaded ")
        elif paras.problem == "puzzle_astar_edu":
            from solver.ceoh.problems.descriptions.puzzle.puzzle_astar_edu import run
            self.prob = run.PUZZLE_ASTAR(code_string=None, paras=paras)
            print("- Prob " + paras.problem + " loaded ")
        else:
            print("problem "+paras.problem+" not found!")


    def get_problem(self):

        return self.prob
