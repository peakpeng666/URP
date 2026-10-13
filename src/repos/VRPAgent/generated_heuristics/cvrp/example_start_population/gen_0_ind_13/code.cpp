#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_to_remove = getRandomNumber(10, 20);

    std::unordered_set<int> selected_set;
    std::vector<int> selected_list;

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(seed_customer);
    selected_list.push_back(seed_customer);

    int expansion_attempts = 0;
    const int max_expansion_attempts_before_new_seed = 100;
    const int max_neighbors_to_check = 10;

    while (selected_list.size() < num_to_remove) {
        if (expansion_attempts >= max_expansion_attempts_before_new_seed) {
            int new_seed_candidate = -1;
            int find_new_seed_attempts = 0;
            const int max_random_pick_attempts = sol.instance.numCustomers * 2;
            while (new_seed_candidate == -1 && find_new_seed_attempts < max_random_pick_attempts) {
                int temp_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_set.find(temp_seed) == selected_set.end()) {
                    new_seed_candidate = temp_seed;
                }
                find_new_seed_attempts++;
            }

            if (new_seed_candidate != -1) {
                selected_set.insert(new_seed_candidate);
                selected_list.push_back(new_seed_candidate);
                expansion_attempts = 0;
                continue;
            } else {
                break;
            }
        }

        int rand_idx = getRandomNumber(0, selected_list.size() - 1);
        int current_customer_id = selected_list[rand_idx];

        bool expanded_this_iter = false;
        if (!sol.instance.adj[current_customer_id].empty()) {
            int num_neighbors_to_check_actual = std::min((int)sol.instance.adj[current_customer_id].size(), max_neighbors_to_check);
            for (int i = 0; i < num_neighbors_to_check_actual; ++i) {
                int neighbor_id = sol.instance.adj[current_customer_id][i];
                if (neighbor_id > 0 && neighbor_id <= sol.instance.numCustomers && selected_set.find(neighbor_id) == selected_set.end()) {
                    selected_set.insert(neighbor_id);
                    selected_list.push_back(neighbor_id);
                    expanded_this_iter = true;
                    break;
                }
            }
        }

        if (expanded_this_iter) {
            expansion_attempts = 0;
        } else {
            expansion_attempts++;
        }
    }

    return selected_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_priorities;
    customer_priorities.reserve(customers.size());

    for (int customer_id : customers) {
        float dist_to_depot = instance.distanceMatrix[0][customer_id];
        float customer_demand = static_cast<float>(instance.demand[customer_id]);

        float priority_score = customer_demand * 5.0f +
                               dist_to_depot * 0.5f +
                               getRandomFractionFast() * 20.0f;

        customer_priorities.push_back({priority_score, customer_id});
    }

    std::sort(customer_priorities.begin(), customer_priorities.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_priorities[i].second;
    }
}