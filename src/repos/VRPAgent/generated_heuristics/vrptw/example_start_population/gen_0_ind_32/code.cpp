#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    selectedCustomers.insert(getRandomNumber(1, sol.instance.numCustomers));

    while (selectedCustomers.size() < numCustomersToRemove) {
        float pick_strategy_rand = getRandomFractionFast();
        
        if (selectedCustomers.empty() || pick_strategy_rand < 0.2f) {
            int customer_to_add;
            do {
                customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomers.count(customer_to_add));
            selectedCustomers.insert(customer_to_add);
        } else {
            std::vector<int> temp_selected(selectedCustomers.begin(), selectedCustomers.end());
            int anchor_customer_idx = getRandomNumber(0, static_cast<int>(temp_selected.size()) - 1);
            int anchor_customer = temp_selected[anchor_customer_idx];

            bool added_neighbor = false;
            for (int neighbor_id : sol.instance.adj[anchor_customer]) {
                if (neighbor_id > 0 && neighbor_id <= sol.instance.numCustomers && !selectedCustomers.count(neighbor_id)) {
                    selectedCustomers.insert(neighbor_id);
                    added_neighbor = true;
                    break; 
                }
            }

            if (!added_neighbor) {
                int customer_to_add;
                do {
                    customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
                } while (selectedCustomers.count(customer_to_add));
                selectedCustomers.insert(customer_to_add);
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customer_id : customers) {
        float base_score = instance.TW_Width[customer_id];
        float noise_factor = 1.0f + getRandomFraction(-0.1f, 0.1f); 
        float perturbed_score = base_score * noise_factor;
        
        if (perturbed_score < 0.0f) {
            perturbed_score = 0.0f;
        }

        customerScores.push_back({perturbed_score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first < b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}