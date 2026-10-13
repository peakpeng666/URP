#include "AgentDesigned.h"
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20);

    std::vector<int> selectedCustomersList;
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> potentialExpansionNodes;

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersList.push_back(initialCustomer);
    selectedCustomersSet.insert(initialCustomer);
    potentialExpansionNodes.push_back(initialCustomer);

    while (selectedCustomersList.size() < numCustomersToRemove) {
        if (potentialExpansionNodes.empty()) {
            int newRandomCustomer = -1;
            int attempts = 0;
            const int maxAttempts = sol.instance.numCustomers * 2; // Prevent infinite loop if almost all customers are selected
            while (newRandomCustomer == -1 || selectedCustomersSet.count(newRandomCustomer) > 0) {
                newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
                if (attempts > maxAttempts) { // All customers are selected, or very few remaining
                    return selectedCustomersList; // Return what we have
                }
            }
            selectedCustomersList.push_back(newRandomCustomer);
            selectedCustomersSet.insert(newRandomCustomer);
            potentialExpansionNodes.push_back(newRandomCustomer);
            continue;
        }

        int baseCustomerIdx = getRandomNumber(0, potentialExpansionNodes.size() - 1);
        int baseCustomer = potentialExpansionNodes[baseCustomerIdx];

        std::vector<int> eligibleNeighbors;
        int neighborsToConsider = std::min((int)sol.instance.adj[baseCustomer].size(), 10);

        for (int i = 0; i < neighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[baseCustomer][i];
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                eligibleNeighbors.push_back(neighbor);
            }
        }

        if (eligibleNeighbors.empty()) {
            potentialExpansionNodes.erase(potentialExpansionNodes.begin() + baseCustomerIdx);
        } else {
            int selectedNeighbor = eligibleNeighbors[getRandomNumber(0, eligibleNeighbors.size() - 1)];
            selectedCustomersList.push_back(selectedNeighbor);
            selectedCustomersSet.insert(selectedNeighbor);
            potentialExpansionNodes.push_back(selectedNeighbor);
        }
    }

    return selectedCustomersList;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerDistances;
    for (int customerId : customers) {
        float actualDistance = instance.distanceMatrix[0][customerId];
        float noiseFactor = 0.1f;
        float perturbedDistance = actualDistance * (1.0f + (getRandomFractionFast() * 2.0f - 1.0f) * noiseFactor);
        customerDistances.push_back({perturbedDistance, customerId});
    }

    std::sort(customerDistances.rbegin(), customerDistances.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerDistances[i].second;
    }
}