#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(15, 30); 

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_seed);
    selectedCustomersList.push_back(initial_seed);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        float decision_roll = getRandomFractionFast();

        bool customer_added_in_current_iter = false;

        if (decision_roll < 0.8 && !selectedCustomersList.empty()) {
            int pivot_idx = getRandomNumber(0, selectedCustomersList.size() - 1);
            int pivot_customer = selectedCustomersList[pivot_idx];

            int max_neighbor_idx_to_consider = std::min((int)sol.instance.adj[pivot_customer].size() - 1, 9);

            for (int attempt = 0; attempt < 5; ++attempt) {
                if (max_neighbor_idx_to_consider < 0) break;
                int neighbor_pos_in_adj = getRandomNumber(0, max_neighbor_idx_to_consider);
                int candidate_neighbor = sol.instance.adj[pivot_customer][neighbor_pos_in_adj];

                if (selectedCustomersSet.find(candidate_neighbor) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(candidate_neighbor);
                    selectedCustomersList.push_back(candidate_neighbor);
                    customer_added_in_current_iter = true;
                    break;
                }
            }
        }

        if (!customer_added_in_current_iter) {
            int new_customer;
            do {
                new_customer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.count(new_customer));
            
            selectedCustomersSet.insert(new_customer);
            selectedCustomersList.push_back(new_customer);
        }
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float score = 0.0f;

        score += static_cast<float>(instance.demand[customer_id]); 

        score += instance.distanceMatrix[0][customer_id] * 0.1f; 
        
        score += getRandomFractionFast() * 0.01f; 

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.rbegin(), scored_customers.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}