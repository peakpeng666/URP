#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility> // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_customers_to_remove = getRandomNumber(10, 20);

    std::unordered_set<int> selected_set;
    std::vector<int> selected_list;

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(seed_customer);
    selected_list.push_back(seed_customer);

    int attempts_per_selection = 0;
    const int max_attempts_per_selection = 50;

    while (selected_list.size() < num_customers_to_remove) {
        bool customer_added_in_this_iteration = false;
        attempts_per_selection = 0;

        while (!customer_added_in_this_iteration && attempts_per_selection < max_attempts_per_selection) {
            int pivot_customer_idx = selected_list[getRandomNumber(0, selected_list.size() - 1)];

            int num_neighbors_to_check = std::min((int)sol.instance.adj[pivot_customer_idx].size(), getRandomNumber(5, 15));

            std::vector<int> viable_neighbors;
            for (int i = 0; i < num_neighbors_to_check; ++i) {
                int neighbor_node = sol.instance.adj[pivot_customer_idx][i];
                if (neighbor_node != 0 && !selected_set.count(neighbor_node)) {
                    viable_neighbors.push_back(neighbor_node);
                }
            }

            if (!viable_neighbors.empty()) {
                int selected_neighbor_idx_in_viable = getRandomNumber(0, std::min((int)viable_neighbors.size() - 1, 2));
                int customer_to_add = viable_neighbors[selected_neighbor_idx_in_viable];

                selected_set.insert(customer_to_add);
                selected_list.push_back(customer_to_add);
                customer_added_in_this_iteration = true;
            } else {
                attempts_per_selection++;
            }
        }

        if (!customer_added_in_this_iteration) {
            int fallback_customer = -1;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (!selected_set.count(i)) {
                    fallback_customer = i;
                    break;
                }
            }
            if (fallback_customer != -1) {
                selected_set.insert(fallback_customer);
                selected_list.push_back(fallback_customer);
            } else {
                break;
            }
        }
    }
    return selected_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_distances;
    customer_distances.reserve(customers.size());
    for (int customer_id : customers) {
        customer_distances.push_back({instance.distanceMatrix[0][customer_id], customer_id});
    }

    std::sort(customer_distances.begin(), customer_distances.end());

    std::vector<int> sorted_customers_stochastic;
    sorted_customers_stochastic.reserve(customers.size());

    std::unordered_set<int> remaining_customers_indices;
    for (size_t i = 0; i < customer_distances.size(); ++i) {
        remaining_customers_indices.insert(i);
    }

    while (!remaining_customers_indices.empty()) {
        int pool_size = std::min((int)remaining_customers_indices.size(), getRandomNumber(2, 5));

        std::vector<int> current_pool_indices;
        int count = 0;
        for (size_t i = 0; i < customer_distances.size() && count < pool_size; ++i) {
            if (remaining_customers_indices.count(i)) {
                current_pool_indices.push_back(i);
                count++;
            }
        }

        int selected_idx_in_pool = getRandomNumber(0, current_pool_indices.size() - 1);
        int selected_customer_original_idx = current_pool_indices[selected_idx_in_pool];

        sorted_customers_stochastic.push_back(customer_distances[selected_customer_original_idx].second);
        remaining_customers_indices.erase(selected_customer_original_idx);
    }

    customers = sorted_customers_stochastic;
}