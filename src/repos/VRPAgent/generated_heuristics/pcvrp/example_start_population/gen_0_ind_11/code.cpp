#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<bool> isSelected(sol.instance.numCustomers + 1, false);

    const int MIN_REMOVE = 15;
    const int MAX_REMOVE = 30;
    int numCustomersToRemove = getRandomNumber(MIN_REMOVE, MAX_REMOVE);

    const float EXPANSION_PROBABILITY = 0.8f;
    const int MAX_NEIGHBORS_TO_CONSIDER = 5;

    std::vector<int> candidatesForExpansion;

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_seed);
    isSelected[initial_seed] = true;
    candidatesForExpansion.push_back(initial_seed);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesForExpansion.empty()) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            const int MAX_ATTEMPTS_FOR_NEW_SEED = 1000;
            int attempts = 0;
            while (isSelected[new_seed] && attempts < MAX_ATTEMPTS_FOR_NEW_SEED) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (isSelected[new_seed]) { 
                break;
            }
            selectedCustomersSet.insert(new_seed);
            isSelected[new_seed] = true;
            candidatesForExpansion.push_back(new_seed);
            if (selectedCustomersSet.size() == numCustomersToRemove) {
                break;
            }
        }

        int rand_idx = getRandomNumber(0, candidatesForExpansion.size() - 1);
        int current_node = candidatesForExpansion[rand_idx];
        candidatesForExpansion.erase(candidatesForExpansion.begin() + rand_idx);

        int neighbors_considered = 0;
        for (int neighbor : sol.instance.adj[current_node]) {
            if (neighbors_considered >= MAX_NEIGHBORS_TO_CONSIDER) {
                break;
            }
            if (!isSelected[neighbor]) {
                if (getRandomFractionFast() < EXPANSION_PROBABILITY) {
                    selectedCustomersSet.insert(neighbor);
                    isSelected[neighbor] = true;
                    candidatesForExpansion.push_back(neighbor);
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        goto end_selection_loop; 
                    }
                }
            }
            neighbors_considered++;
        }
    }

end_selection_loop:;
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;

    const float DISTANCE_PENALTY_FACTOR = 0.5f;

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id] - (instance.distanceMatrix[0][customer_id] * DISTANCE_PENALTY_FACTOR);
        score += getRandomFractionFast() * 0.001f * instance.total_prizes;
        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}