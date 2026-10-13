#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> customersToExpand;

    int numCustomersToRemove = getRandomNumber(15, 35);

    int initial_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    
    selectedCustomersSet.insert(initial_seed_customer);
    customersToExpand.push_back(initial_seed_customer);
    
    float prob_add_neighbor_base = 0.7f;
    float prob_new_seed = 0.15f;         

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool expanded_this_iter = false;

        if (!customersToExpand.empty()) {
            int idx_to_expand = getRandomNumber(0, customersToExpand.size() - 1);
            int current_customer = customersToExpand[idx_to_expand];
            customersToExpand.erase(customersToExpand.begin() + idx_to_expand);

            int num_neighbors_to_check = std::min((int)sol.instance.adj[current_customer].size(), getRandomNumber(5, 15));

            for (int i = 0; i < num_neighbors_to_check; ++i) {
                int neighbor = sol.instance.adj[current_customer][i];

                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    float prob_add_this_neighbor = prob_add_neighbor_base + getRandomFraction(-0.1f, 0.1f);

                    if (getRandomFractionFast() < prob_add_this_neighbor) {
                        selectedCustomersSet.insert(neighbor);
                        customersToExpand.push_back(neighbor);
                        expanded_this_iter = true;
                        if (selectedCustomersSet.size() >= numCustomersToRemove) break;
                    }
                }
            }
        }

        if (!expanded_this_iter || customersToExpand.empty() || getRandomFractionFast() < prob_new_seed) {
            int new_seed_customer = -1;
            int attempts = 0;
            const int max_attempts = sol.instance.numCustomers * 2;

            while (attempts < max_attempts) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potential_seed) == selectedCustomersSet.end()) {
                    new_seed_customer = potential_seed;
                    break;
                }
                attempts++;
            }

            if (new_seed_customer != -1) {
                selectedCustomersSet.insert(new_seed_customer);
                customersToExpand.push_back(new_seed_customer);
                if (selectedCustomersSet.size() >= numCustomersToRemove) break;
            } else if (selectedCustomersSet.size() < numCustomersToRemove) {
                 while (selectedCustomersSet.size() < numCustomersToRemove) {
                    int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                    selectedCustomersSet.insert(randomCustomer);
                 }
                 break;
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    float prize_weight = 1.0f;
    float depot_distance_weight = 0.5f;

    for (int customer_id : customers) {
        float score = 0.0f;

        score += prize_weight * instance.prizes[customer_id];

        score -= depot_distance_weight * instance.distanceMatrix[0][customer_id];

        float random_jitter_range = (instance.total_prizes / instance.numCustomers) * 0.5f;
        score += getRandomFraction(-random_jitter_range, random_jitter_range);

        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}