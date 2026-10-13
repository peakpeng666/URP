#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::shuffle
#include <vector>
#include <utility>   // For std::pair

#include "Utils.h" // For getRandomNumber, getRandomFractionFast

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_list;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove >= sol.instance.numCustomers) {
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            selected_list.push_back(i);
        }
        return selected_list;
    }

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(seed_customer);
    selected_list.push_back(seed_customer);

    const int k_neighbors_to_consider = 7;

    while (selected_list.size() < numCustomersToRemove) {
        int expansion_source_idx = getRandomNumber(0, selected_list.size() - 1);
        int expansion_source_customer = selected_list[expansion_source_idx];

        std::vector<int> potential_neighbors;
        if (expansion_source_customer >= 0 && expansion_source_customer < sol.instance.adj.size()) {
            for (int neighbor_node : sol.instance.adj[expansion_source_customer]) {
                if (neighbor_node != 0 && selected_set.find(neighbor_node) == selected_set.end()) {
                    potential_neighbors.push_back(neighbor_node);
                    if (potential_neighbors.size() >= k_neighbors_to_consider) {
                        break; 
                    }
                }
            }
        }
        
        if (!potential_neighbors.empty()) {
            int idx_to_add = getRandomNumber(0, potential_neighbors.size() - 1);
            int customer_to_add = potential_neighbors[idx_to_add];
            selected_set.insert(customer_to_add);
            selected_list.push_back(customer_to_add);
        } else {
            int new_random_customer;
            int attempts = 0;
            const int max_attempts = sol.instance.numCustomers * 2; // Prevent infinite loop on small instances or nearly full selection

            do {
                new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
                if (attempts > max_attempts) break; // Break if too many attempts and can't find unique customer
            } while (selected_set.count(new_random_customer));
            
            if (!selected_set.count(new_random_customer) && selected_list.size() < sol.instance.numCustomers) {
                selected_set.insert(new_random_customer);
                selected_list.push_back(new_random_customer);
            } else if (selected_list.size() >= sol.instance.numCustomers) {
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

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    const float stochastic_factor = 0.1f; 

    for (int customer_id : customers) {
        float distance_to_depot = instance.distanceMatrix[customer_id][0];
        int demand = instance.demand[customer_id];

        float base_score = distance_to_depot * (demand + 1e-3f); 

        float noisy_score = base_score + (getRandomFractionFast() * stochastic_factor); 

        customer_scores.push_back({noisy_score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}