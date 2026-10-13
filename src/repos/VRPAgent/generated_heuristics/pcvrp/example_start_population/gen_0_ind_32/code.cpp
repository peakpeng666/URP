#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomersToRemove = getRandomNumber(15, 35);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersList.push_back(seedCustomer);

    int attempts = 0;
    const int max_attempts_multiplier = 5;

    while (selectedCustomersSet.size() < numCustomersToRemove && attempts < numCustomersToRemove * max_attempts_multiplier) {
        int expandFromCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];

        const std::vector<int>& neighbors = sol.instance.adj[expandFromCustomer - 1];

        if (!neighbors.empty()) {
            int neighbor_idx_limit = std::min((int)neighbors.size() - 1, 15);
            if (neighbor_idx_limit < 0) {
                attempts++;
                continue;
            }
            int chosen_neighbor_idx = getRandomNumber(0, neighbor_idx_limit);
            int candidateCustomer = neighbors[chosen_neighbor_idx];

            if (candidateCustomer != 0 && selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(candidateCustomer);
                selectedCustomersList.push_back(candidateCustomer);
                attempts = 0;
            } else {
                attempts++;
            }
        } else {
            attempts++;
            if (getRandomFractionFast() < 0.1f) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(randomCustomer);
                    selectedCustomersList.push_back(randomCustomer);
                    attempts = 0;
                }
            }
        }
    }
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    const float prize_weight = 1.0f;
    const float distance_weight = 0.1f;
    const float random_perturbation_magnitude = 0.01f;

    for (int customer_id : customers) {
        float score = 0.0f;

        score += instance.prizes[customer_id] * prize_weight;

        score -= instance.distanceMatrix[0][customer_id] * distance_weight;

        score += (getRandomFractionFast() - 0.5f) * random_perturbation_magnitude;

        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}