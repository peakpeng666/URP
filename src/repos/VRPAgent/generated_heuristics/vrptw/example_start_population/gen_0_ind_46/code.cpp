#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVector;

    int numCustomersToRemove = getRandomNumber(10, 20);

    // Initial random seed customer
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVector.push_back(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool addedCustomerInIteration = false;

        // Try to expand from an already selected customer's neighborhood
        if (!selectedCustomersVector.empty()) {
            int sourceCustomerIdx = getRandomNumber(0, selectedCustomersVector.size() - 1);
            int sourceCustomer = selectedCustomersVector[sourceCustomerIdx];

            int numNeighborsToConsider = std::min((int)sol.instance.adj[sourceCustomer].size(), 10);
            
            std::vector<int> neighborsToShuffle;
            for (int i = 0; i < numNeighborsToConsider; ++i) {
                neighborsToShuffle.push_back(sol.instance.adj[sourceCustomer][i]);
            }
            static thread_local std::mt19937 gen(std::random_device{}());
            std::shuffle(neighborsToShuffle.begin(), neighborsToShuffle.end(), gen);

            for (int neighbor : neighborsToShuffle) {
                if (neighbor > 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(neighbor);
                    selectedCustomersVector.push_back(neighbor);
                    addedCustomerInIteration = true;
                    break;
                }
            }
        }
        
        // Fallback: If no suitable neighbor was found or vector was empty, pick a completely random unselected customer
        if (!addedCustomerInIteration && selectedCustomersSet.size() < numCustomersToRemove) {
            int randomCustomer;
            do {
                randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.find(randomCustomer) != selectedCustomersSet.end());
            selectedCustomersSet.insert(randomCustomer);
            selectedCustomersVector.push_back(randomCustomer);
        }
    }

    return selectedCustomersVector;
}

struct CustomerSortInfo {
    int customerId;
    float sortKey;
};

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<CustomerSortInfo> sortInfos;
    sortInfos.reserve(customers.size());

    float perturbationMagnitude = 0.05f; // Relative perturbation, e.g., +/- 5% of TW_Width
                                        // or could be a small absolute value for consistency.
                                        // A simple percentage avoids needing global max TW_Width.

    for (int customerId : customers) {
        float baseKey = instance.TW_Width[customerId];
        float randomFactor = 1.0f + getRandomFraction(-perturbationMagnitude, perturbationMagnitude);
        float perturbedKey = baseKey * randomFactor;
        
        // Ensure non-negative key (time window widths should be >= 0)
        if (perturbedKey < 0.0f) {
            perturbedKey = 0.0f;
        }

        sortInfos.push_back({customerId, perturbedKey});
    }

    std::sort(sortInfos.begin(), sortInfos.end(), [](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        return a.sortKey < b.sortKey;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sortInfos[i].customerId;
    }
}