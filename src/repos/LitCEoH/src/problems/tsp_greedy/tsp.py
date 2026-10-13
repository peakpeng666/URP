import numpy as np

class TSP:

    def __init__(self, instances, n_instance, problem_size) -> None:

        self.ndelay = 1
        self.neighbor_size = np.minimum(50, self.problem_size)

        self.n_instance = n_instance
        self.problem_size = problem_size

        self.running_time = 10

        self.instance_data = instances


    def tour_cost(self, instance, solution, problem_size):
        cost = 0
        for j in range(problem_size - 1):
            cost += np.linalg.norm(instance[int(solution[j])] - instance[int(solution[j + 1])])
        cost += np.linalg.norm(instance[int(solution[-1])] - instance[int(solution[0])])
        return cost


    def generate_neighborhood_matrix(self, instance):
        instance = np.array(instance)
        n = len(instance)
        neighborhood_matrix = np.zeros((n, n), dtype=int)

        for i in range(n):
            distances = np.linalg.norm(instance[i] - instance, axis=1)
            sorted_indices = np.argsort(distances)  # sort indices based on distances
            neighborhood_matrix[i] = sorted_indices

        return neighborhood_matrix


    # @func_set_timeout(5)
    def greedy(self, eva):
        dis = np.ones(self.n_instance)
        n_ins = 0
        for instance, distance_matrix in self.instance_data:

            # get neighborhood matrix
            neighbor_matrix = self.generate_neighborhood_matrix(instance)

            destination_node = 0

            current_node = 0

            route = np.zeros(self.problem_size)
            # print(">>> Step 0 : select node "+str(instance[0][0])+", "+str(instance[0][1]))
            for i in range(1, self.problem_size - 1):

                near_nodes = neighbor_matrix[current_node][1:]

                mask = ~np.isin(near_nodes, route[:i])

                unvisited_near_nodes = near_nodes[mask]

                unvisited_near_size = np.minimum(self.neighbor_size, unvisited_near_nodes.size)

                unvisited_near_nodes = unvisited_near_nodes[:unvisited_near_size]

                next_node = eva.select_next_node(current_node, destination_node, unvisited_near_nodes, distance_matrix)

                if next_node in route:
                    # print("wrong algorithm select duplicate node, retrying ...")
                    return None

                current_node = next_node

                route[i] = current_node

                # print(">>> Step "+str(i)+": select node "+str(instance[current_node][0])+", "+str(instance[current_node][1]))

            mask = ~np.isin(np.arange(self.problem_size), route[:self.problem_size - 1])

            last_node = np.arange(self.problem_size)[mask]

            current_node = last_node[0]

            route[self.problem_size - 1] = current_node

            # print(">>> Step "+str(self.problem_size-1)+": select node "+str(instance[current_node][0])+", "+str(instance[current_node][1]))

            LLM_dis = self.tour_cost(instance, route, self.problem_size)
            dis[n_ins] = LLM_dis

            n_ins += 1
            if n_ins == self.n_instance:
                break
            # self.route_plot(instance,route,self.oracle[n_ins])

        ave_dis = np.average(dis)
        # print("average dis: ",ave_dis)
        return ave_dis