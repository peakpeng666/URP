import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))

import unittest

import types
from problems.vrp.problem_class import CeohRoutefinderProblem
from solver.ceoh.utils.getParas import Paras

code_string = """
def best_first_heuristic(data):
    distance_matrix = data['distance_matrix']
    duration_matrix = data['duration_matrix']
    demands = data['demands']
    vehicle_capacities = data['vehicle_capacities']
    num_vehicles = data['num_vehicles']
    starts = data['vehicle_start_depots']
    ends = data['vehicle_end_depots']
    time_windows = data['time_windows']

    depot = starts[0]
    num_locations = len(distance_matrix)
    customers = list(range(1, num_locations))

    # Initial routes: one customer per vehicle
    routes = [[depot, customer, depot] for customer in customers[:num_vehicles]]

    savings_list = []
    for i in customers:
        for j in customers:
            if i != j:
                savings = distance_matrix[depot][i] + distance_matrix[depot][j] - distance_matrix[i][j]
                savings_list.append((savings, i, j))

    savings_list.sort(reverse=True, key=lambda x: x[0])

    def is_time_window_feasible(route):
        time = 0
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            time = max(time, time_windows[from_node][0])  # Wait if early
            travel_time = duration_matrix[from_node][to_node]
            time += travel_time
            if time > time_windows[to_node][1]:  # Too late
                return False
        return True

    for savings, i, j in savings_list:
        route_i = None
        route_j = None

        for route in routes:
            if i in route:
                route_i = route
            if j in route:
                route_j = route

        if route_i and route_j and route_i != route_j:
            demand_i = sum(demands[node] for node in route_i if node != depot)
            demand_j = sum(demands[node] for node in route_j if node != depot)
            combined_demand = demand_i + demand_j

            if combined_demand <= vehicle_capacities[routes.index(route_i)]:
                if (route_i[-2] == i and route_j[1] == j):
                    new_route = route_i[:-1] + route_j[1:]
                elif (route_j[-2] == j and route_i[1] == i):
                    new_route = route_j[:-1] + route_i[1:]
                else:
                    continue

                if is_time_window_feasible(new_route):
                    routes.remove(route_i)
                    routes.remove(route_j)
                    routes.append(new_route)

    return routes
"""


class TestVRPTW(unittest.TestCase):

    def setUp(self):

        self.VRP_PROBLEM = 'vrptw'
        self.PRINTOUT = False

        os.environ["EOH_PROBLEM"] = "cvrp"

        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        base_path = f"{self.dir_path}/../.."

        os.environ["BASE_PATH"]  = base_path

        os.environ["INSTANCES_PATH"] = f"{base_path}/data/mr_examples"
        os.environ["OUTPUT_PATH"] = f"{base_path}/ceoh_results"

    def test_run(self):

        rf_problem_class = CeohRoutefinderProblem(self.VRP_PROBLEM, printout=self.PRINTOUT)

        heuristic_module = types.ModuleType("heuristic_module")
        exec(code_string, heuristic_module.__dict__)
        # Attach the original code string to the module for use in process-based execution
        heuristic_module.code_string = code_string

        paras_instance = Paras()
        # add eoh_experiment_file to paras
        paras_instance.set_paras(
            eoh_experiment_file=f"{self.dir_path}/../../data/vrp_instances/vrptw/test/50.npz",
        )

        fitness, details = rf_problem_class.eval_heuristic(heuristic_module, paras_instance)

        self.assertGreater(fitness, 0)

if __name__ == '__main__':
    unittest.main()
