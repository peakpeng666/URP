#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> removed_customers_set;
    std::vector<int> current_cluster_nodes;

    int num_to_remove = getRandomNumber(10, 20);

    if (num_to_remove <= 0) {
        num_to_remove = 1;
    }

    int seed_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    removed_customers_set.insert(seed_customer_idx);
    current_cluster_nodes.push_back(seed_customer_idx);

    int attempts = 0;
    const int max_selection_attempts = num_to_remove * 5;
    const int neighbor_search_limit = 10;

    while (removed_customers_set.size() < num_to_remove && attempts < max_selection_attempts) {
        attempts++;

        int expand_from_customer_idx = current_cluster_nodes[getRandomNumber(0, current_cluster_nodes.size() - 1)];

        bool found_new_customer = false;
        for (size_t i = 0; i < std::min((size_t)neighbor_search_limit, sol.instance.adj[expand_from_customer_idx].size()); ++i) {
            int potential_neighbor_idx = sol.instance.adj[expand_from_customer_idx][i];

            if (potential_neighbor_idx != 0 && removed_customers_set.find(potential_neighbor_idx) == removed_customers_set.end()) {
                removed_customers_set.insert(potential_neighbor_idx);
                current_cluster_nodes.push_back(potential_neighbor_idx);
                found_new_customer = true;
                break;
            }
        }

        if (!found_new_customer) {
            int fallback_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
            if (removed_customers_set.find(fallback_customer_idx) == removed_customers_set.end()) {
                removed_customers_set.insert(fallback_customer_idx);
                current_cluster_nodes.push_back(fallback_customer_idx);
            }
        }
    }

    while (removed_customers_set.size() < num_to_remove) {
        int random_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
        removed_customers_set.insert(random_customer_idx);
    }

    return std::vector<int>(removed_customers_set.begin(), removed_customers_set.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scored_list;
    customer_scored_list.reserve(customers.size());

    float demand_weight = 1000.0f;
    float distance_from_depot_weight = 1.0f;

    float stochastic_range_half = 50.0f; 

    for (int customer_id : customers) {
        float current_customer_demand = static_cast<float>(instance.demand[customer_id]);
        float current_dist_from_depot = instance.distanceMatrix[0][customer_id];

        float score = (current_customer_demand * demand_weight) +
                      (current_dist_from_depot * distance_from_depot_weight);

        score += (getRandomFractionFast() * 2.0f - 1.0f) * stochastic_range_half;

        customer_scored_list.push_back({score, customer_id});
    }

    std::sort(customer_scored_list.begin(), customer_scored_list.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customer_scored_list.size(); ++i) {
        customers[i] = customer_scored_list[i].second;
    }
}