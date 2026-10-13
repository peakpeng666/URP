#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include "Utils.h"
#include <algorithm>
#include <vector>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVector;

    int numCustomersToRemove = getRandomNumber(10, 25);

    std::vector<int> expansionQueue;

    auto add_customer_to_selection = [&](int customer_id) {
        if (selectedCustomersSet.insert(customer_id).second) {
            selectedCustomersVector.push_back(customer_id);
            expansionQueue.push_back(customer_id);
            return true;
        }
        return false;
    };

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    add_customer_to_selection(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (expansionQueue.empty()) {
            int new_seed = -1;
            int attempts = 0;
            while (attempts < 100 && new_seed == -1) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potential_seed) == selectedCustomersSet.end()) {
                    new_seed = potential_seed;
                }
                attempts++;
            }

            if (new_seed != -1) {
                add_customer_to_selection(new_seed);
            } else {
                break;
            }
        }

        int current_idx_in_queue = getRandomNumber(0, static_cast<int>(expansionQueue.size()) - 1);
        int current_customer_to_expand_from = expansionQueue[current_idx_in_queue];

        const std::vector<int>& neighbors = sol.instance.adj[current_customer_to_expand_from];
        int num_neighbors_to_check = std::min(static_cast<int>(neighbors.size()), 10);

        std::vector<int> potentialNewNeighbors;
        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor = neighbors[i];
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                potentialNewNeighbors.push_back(neighbor);
            }
        }

        if (!potentialNewNeighbors.empty()) {
            int neighbor_to_add = potentialNewNeighbors[getRandomNumber(0, static_cast<int>(potentialNewNeighbors.size()) - 1)];
            add_customer_to_selection(neighbor_to_add);
        }
    }

    return selectedCustomersVector;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    for (int customer_id : customers) {
        float score = static_cast<float>(instance.demand[customer_id]) * instance.distanceMatrix[0][customer_id];
        score -= instance.prizes[customer_id];
        customer_scores.push_back({score, customer_id});
    }

    std::vector<int> sorted_customers_llm;
    std::unordered_set<int> remaining_customers_set(customers.begin(), customers.end());

    while (!remaining_customers_set.empty()) {
        std::vector<std::pair<float, int>> current_candidates;
        for (const auto& p : customer_scores) {
            if (remaining_customers_set.count(p.second)) {
                current_candidates.push_back(p);
            }
        }

        std::sort(current_candidates.begin(), current_candidates.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });

        int num_top_candidates_to_consider = std::min(static_cast<int>(current_candidates.size()), 10);
        
        int selected_idx_in_candidates = 0;
        if (num_top_candidates_to_consider > 1) {
            selected_idx_in_candidates = getRandomNumber(0, num_top_candidates_to_consider - 1);
        }
        
        int customer_to_add = current_candidates[selected_idx_in_candidates].second;
        sorted_customers_llm.push_back(customer_to_add);
        remaining_customers_set.erase(customer_to_add);
    }

    customers = sorted_customers_llm;
}