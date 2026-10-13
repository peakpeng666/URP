#include "AgentDesigned.h"
#include <vector>
#include <unordered_set>
#include <algorithm>
#include <utility>
#include <cmath>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomers = sol.instance.numCustomers;

    int numCustomersToRemove = getRandomNumber(20, 40); 

    if (numCustomersToRemove == 0) {
        return {};
    }

    int seed_customer_id = getRandomNumber(1, numCustomers);
    selectedCustomers.insert(seed_customer_id);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (getRandomFractionFast() < 0.85f) {
            int pivot_idx = getRandomNumber(0, static_cast<int>(selectedCustomers.size()) - 1);
            auto it = selectedCustomers.begin();
            std::advance(it, pivot_idx);
            int pivot_customer_id = *it;

            const auto& neighbors = sol.instance.adj[pivot_customer_id];

            bool neighbor_added = false;
            for (size_t i = 0; i < neighbors.size(); ++i) {
                int potential_neighbor = neighbors[i];
                if (potential_neighbor == 0 || potential_neighbor > numCustomers) {
                    continue;
                }

                float selection_prob = 0.9f * (1.0f - static_cast<float>(i) / neighbors.size());
                if (getRandomFractionFast() < selection_prob && selectedCustomers.find(potential_neighbor) == selectedCustomers.end()) {
                    selectedCustomers.insert(potential_neighbor);
                    neighbor_added = true;
                    break; 
                }
            }
            if (!neighbor_added) {
                selectedCustomers.insert(getRandomNumber(1, numCustomers));
            }
        } else { 
            selectedCustomers.insert(getRandomNumber(1, numCustomers));
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float random_perturbation_factor = 0.05f; 

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        
        float stochastic_prize = prize + (getRandomFraction(-1.0f, 1.0f) * prize * random_perturbation_factor);
        
        stochastic_prize = std::max(0.0f, stochastic_prize);

        customer_scores.push_back({-stochastic_prize, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}