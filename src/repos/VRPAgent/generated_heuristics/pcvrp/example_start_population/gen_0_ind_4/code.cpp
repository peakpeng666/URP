#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>

// Customer selection heuristic for LNS
// Selects a subset of customers to remove based on proximity, ensuring diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 25);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    std::vector<int> candidates_for_expansion;

    int seed_customer = -1;
    std::vector<int> visited_customers_in_solution;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            visited_customers_in_solution.push_back(i);
        }
    }

    if (!visited_customers_in_solution.empty()) {
        seed_customer = visited_customers_in_solution[getRandomNumber(0, visited_customers_in_solution.size() - 1)];
    } else {
        seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    }

    selectedCustomers.insert(seed_customer);
    candidates_for_expansion.push_back(seed_customer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidates_for_expansion.empty()) {
            int fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomers.find(fallback_customer) == selectedCustomers.end()) {
                selectedCustomers.insert(fallback_customer);
                candidates_for_expansion.push_back(fallback_customer);
            }
            continue; 
        }

        int current_idx_in_candidates = getRandomNumber(0, candidates_for_expansion.size() - 1);
        int customer_to_expand_from = candidates_for_expansion[current_idx_in_candidates];
        
        candidates_for_expansion.erase(candidates_for_expansion.begin() + current_idx_in_candidates);

        int num_neighbors_to_check = std::min((int)sol.instance.adj[customer_to_expand_from].size(), 10 + getRandomNumber(0, 5));
        
        std::vector<int> potential_new_selections;
        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor = sol.instance.adj[customer_to_expand_from][i];
            if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                potential_new_selections.push_back(neighbor);
            }
        }

        if (!potential_new_selections.empty()) {
            int chosen_neighbor = potential_new_selections[getRandomNumber(0, potential_new_selections.size() - 1)];
            selectedCustomers.insert(chosen_neighbor);
            candidates_for_expansion.push_back(chosen_neighbor);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers
// This function does NOT have access to the 'Solution' object.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    const float LARGE_METRIC_PENALTY = instance.total_prizes * 100.0f + 1.0f; 

    for (int customer_id : customers) {
        float score = 0.0f;

        float prize_to_demand_ratio = instance.prizes[customer_id];
        if (instance.demand[customer_id] > 0) {
            prize_to_demand_ratio /= instance.demand[customer_id];
        } else {
            prize_to_demand_ratio *= 2.0f; 
        }
        score += prize_to_demand_ratio * 1.0f;

        score += instance.prizes[customer_id] * 0.1f;

        float connectivity_metric = 0.0f;
        if (!instance.adj[customer_id].empty()) {
            connectivity_metric = -instance.distanceMatrix[customer_id][instance.adj[customer_id][0]]; 
        } else {
            connectivity_metric = -LARGE_METRIC_PENALTY;
        }
        score += connectivity_metric * 0.05f;

        float average_prize_per_customer = instance.total_prizes / std::max(1, instance.numCustomers);
        score += getRandomFraction(-0.5f, 0.5f) * average_prize_per_customer * 0.1f;

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}