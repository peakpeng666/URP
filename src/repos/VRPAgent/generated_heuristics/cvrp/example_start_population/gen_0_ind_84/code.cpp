#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomers = sol.instance.numCustomers;
    int minCustomersToRemove = std::max(5, (int)(numCustomers * 0.02));
    int maxCustomersToRemove = std::min(numCustomers, (int)(numCustomers * 0.06));
    int numCustomersToSelect = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToSelect == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersList.push_back(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToSelect) {
        std::vector<std::pair<float, int>> candidateDistances;
        
        for (int i = 1; i <= numCustomers; ++i) {
            if (selectedCustomersSet.count(i) == 0) {
                float min_dist_to_selected = std::numeric_limits<float>::max();
                for (int selected_cust_id : selectedCustomersSet) {
                    min_dist_to_selected = std::min(min_dist_to_selected, sol.instance.distanceMatrix[i][selected_cust_id]);
                }
                candidateDistances.push_back({min_dist_to_selected, i});
            }
        }

        if (candidateDistances.empty()) {
            break;
        }

        std::sort(candidateDistances.begin(), candidateDistances.end());

        int top_k_candidates_pool_size = std::min((int)candidateDistances.size(), std::max(5, (int)(candidateDistances.size() * 0.1)));
        
        if (top_k_candidates_pool_size == 0 && !candidateDistances.empty()) {
            top_k_candidates_pool_size = 1;
        }

        int randomIndexInPool = getRandomNumber(0, top_k_candidates_pool_size - 1);
        int chosenCustomer = candidateDistances[randomIndexInPool].second;
        
        selectedCustomersSet.insert(chosenCustomer);
        selectedCustomersList.push_back(chosenCustomer);
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;

    for (int i = 0; i < customers.size(); ++i) {
        int current_customer_id = customers[i];
        float total_dist_to_others_removed = 0.0f;
        
        for (int j = 0; j < customers.size(); ++j) {
            if (i == j) {
                continue;
            }
            int other_customer_id = customers[j];
            total_dist_to_others_removed += instance.distanceMatrix[current_customer_id][other_customer_id];
        }

        float isolation_score = total_dist_to_others_removed / (customers.size() - 1);

        isolation_score += getRandomFraction(-1.0f, 1.0f) * 0.01f;

        scoredCustomers.push_back({isolation_score, current_customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (int i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}