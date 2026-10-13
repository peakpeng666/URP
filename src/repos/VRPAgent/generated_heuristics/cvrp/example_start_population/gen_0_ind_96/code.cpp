#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers;
    std::vector<int> candidate_seeds_for_expansion;

    int num_to_remove = getRandomNumber(10, 20);

    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers.insert(initial_customer_id);
    candidate_seeds_for_expansion.push_back(initial_customer_id);

    while (selected_customers.size() < num_to_remove) {
        if (candidate_seeds_for_expansion.empty()) {
            std::vector<int> unselected_pool;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selected_customers.find(i) == selected_customers.end()) {
                    unselected_pool.push_back(i);
                }
            }
            if (unselected_pool.empty()) {
                break;
            }
            int new_seed_customer_id = unselected_pool[getRandomNumber(0, unselected_pool.size() - 1)];
            selected_customers.insert(new_seed_customer_id);
            candidate_seeds_for_expansion.push_back(new_seed_customer_id);
            continue;
        }

        int pivot_idx = getRandomNumber(0, candidate_seeds_for_expansion.size() - 1);
        int current_seed = candidate_seeds_for_expansion[pivot_idx];

        std::vector<int> potential_neighbors_to_add;
        int max_neighbors_to_scan = std::min((int)sol.instance.adj[current_seed].size(), 10);

        for (int i = 0; i < max_neighbors_to_scan; ++i) {
            int neighbor_id = sol.instance.adj[current_seed][i];
            if (neighbor_id > 0 && selected_customers.find(neighbor_id) == selected_customers.end()) {
                potential_neighbors_to_add.push_back(neighbor_id);
            }
        }

        if (!potential_neighbors_to_add.empty()) {
            int chosen_neighbor = potential_neighbors_to_add[getRandomNumber(0, potential_neighbors_to_add.size() - 1)];
            selected_customers.insert(chosen_neighbor);
            candidate_seeds_for_expansion.push_back(chosen_neighbor);
        } else {
            std::swap(candidate_seeds_for_expansion[pivot_idx], candidate_seeds_for_expansion.back());
            candidate_seeds_for_expansion.pop_back();
        }
    }

    return std::vector<int>(selected_customers.begin(), selected_customers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float MAX_TYPICAL_CUSTOMER_DEMAND = 100.0f;
    const float MAX_TYPICAL_DISTANCE_TO_DEPOT = 1500.0f;

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float demand_normalized = static_cast<float>(instance.demand[customer_id]) / MAX_TYPICAL_CUSTOMER_DEMAND;
        float distance_normalized = instance.distanceMatrix[customer_id][0] / MAX_TYPICAL_DISTANCE_TO_DEPOT;
        float random_component = getRandomFractionFast();

        float score = (2.0f * demand_normalized) + (1.0f * distance_normalized) + (0.1f * random_component);
        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}