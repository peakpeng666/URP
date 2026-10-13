#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"
#include "Instance.h"
#include "Solution.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> expansion_pool;

    int numCustomersToRemove = getRandomNumber(15, 30);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    while (selectedCustomers_set.size() < numCustomersToRemove) {
        if (expansion_pool.empty()) {
            int new_seed_customer = -1;
            int attempts = 0;
            const int max_attempts_for_new_seed = 1000;

            while (attempts < max_attempts_for_new_seed) {
                new_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers_set.find(new_seed_customer) == selectedCustomers_set.end()) {
                    break;
                }
                attempts++;
            }

            if (new_seed_customer != -1 && selectedCustomers_set.find(new_seed_customer) == selectedCustomers_set.end()) {
                selectedCustomers_set.insert(new_seed_customer);
                expansion_pool.push_back(new_seed_customer);
            } else {
                break;
            }
        }

        int current_idx = getRandomNumber(0, (int)expansion_pool.size() - 1);
        int current_c = expansion_pool[current_idx];

        std::swap(expansion_pool[current_idx], expansion_pool.back());
        expansion_pool.pop_back();

        const std::vector<int>& neighbors_of_c = sol.instance.adj[current_c];
        int num_neighbors_to_check = std::min((int)neighbors_of_c.size(), getRandomNumber(3, 8));

        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor_c = neighbors_of_c[i];
            
            if (neighbor_c == 0 || selectedCustomers_set.find(neighbor_c) != selectedCustomers_set.end()) {
                continue;
            }

            if (getRandomFractionFast() < 0.85f) {
                selectedCustomers_set.insert(neighbor_c);
                expansion_pool.push_back(neighbor_c);

                if (selectedCustomers_set.size() == numCustomersToRemove) {
                    goto end_selection_loop;
                }
            }
        }
    }

end_selection_loop:;

    return std::vector<int>(selectedCustomers_set.begin(), selectedCustomers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = (float)instance.demand[customer_id];
        
        if (customer_id >= 0 && customer_id < instance.distanceMatrix.size() && 0 < instance.distanceMatrix[customer_id].size()) {
             score += instance.distanceMatrix[customer_id][0] * 0.05f;
        }
        score += getRandomFractionFast() * 0.001f;

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.rbegin(), customer_scores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}