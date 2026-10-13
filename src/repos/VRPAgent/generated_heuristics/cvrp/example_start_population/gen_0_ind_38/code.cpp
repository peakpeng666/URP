#include "AgentDesigned.h"
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20);
    if (sol.instance.numCustomers < numCustomersToRemove) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateExpansionSources;

    int initial_seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_seed_customer_id);
    candidateExpansionSources.push_back(initial_seed_customer_id);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidateExpansionSources.empty()) {
            int new_seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
            int safeguard_counter = 0;
            while (selectedCustomersSet.count(new_seed_customer_id) > 0 && safeguard_counter < sol.instance.numCustomers) {
                new_seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
                safeguard_counter++;
            }
            if (selectedCustomersSet.count(new_seed_customer_id) > 0) {
                break;
            }
            selectedCustomersSet.insert(new_seed_customer_id);
            candidateExpansionSources.push_back(new_seed_customer_id);
            if (selectedCustomersSet.size() >= numCustomersToRemove) {
                break;
            }
        }

        int source_idx = getRandomNumber(0, static_cast<int>(candidateExpansionSources.size()) - 1);
        int current_source_customer_id = candidateExpansionSources[source_idx];

        bool added_any_neighbor = false;
        for (int neighbor_id : sol.instance.adj[current_source_customer_id]) {
            if (neighbor_id == 0) continue;

            if (selectedCustomersSet.size() >= numCustomersToRemove) break;

            if (selectedCustomersSet.count(neighbor_id) == 0) {
                selectedCustomersSet.insert(neighbor_id);
                candidateExpansionSources.push_back(neighbor_id);
                added_any_neighbor = true;
                if (getRandomFractionFast() < 0.2f) {
                    // Continue to potentially add another neighbor from this source
                } else {
                    break;
                }
            }
        }

        if (!added_any_neighbor) {
            if (!candidateExpansionSources.empty()) {
                candidateExpansionSources[source_idx] = candidateExpansionSources.back();
                candidateExpansionSources.pop_back();
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float demand_val = static_cast<float>(instance.demand[customer_id]);
        float dist_to_depot_val = instance.distanceMatrix[0][customer_id];
        float score = demand_val * 0.5f + dist_to_depot_val * 0.5f;
        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i + 1 < customer_scores.size(); ++i) {
        if (getRandomFractionFast() < 0.1f) {
            std::swap(customer_scores[i], customer_scores[i+1]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}