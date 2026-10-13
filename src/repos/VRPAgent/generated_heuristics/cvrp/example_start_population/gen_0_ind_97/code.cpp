#include "AgentDesigned.h"
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;
const int MAX_CLUSTER_EXPANSION_ATTEMPTS = 5;

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersList.push_back(initialCustomer);

    while (selectedCustomersList.size() < numCustomersToRemove) {
        int nextCustomerToAdd = -1;
        bool foundViaExpansion = false;

        for (int attempt = 0; attempt < MAX_CLUSTER_EXPANSION_ATTEMPTS; ++attempt) {
            int pivotCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];

            for (int neighbor : sol.instance.adj[pivotCustomer]) {
                if (!selectedCustomersSet.count(neighbor)) {
                    nextCustomerToAdd = neighbor;
                    foundViaExpansion = true;
                    break;
                }
            }
            if (foundViaExpansion) break;
        }

        if (!foundViaExpansion) {
            nextCustomerToAdd = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(nextCustomerToAdd)) {
                nextCustomerToAdd = getRandomNumber(1, sol.instance.numCustomers);
            }
        }

        selectedCustomersSet.insert(nextCustomerToAdd);
        selectedCustomersList.push_back(nextCustomerToAdd);
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerId : customers) {
        float score = static_cast<float>(instance.demand[customerId]);
        score += getRandomFractionFast() * (instance.vehicleCapacity * 0.1f);
        scoredCustomers.push_back({score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}