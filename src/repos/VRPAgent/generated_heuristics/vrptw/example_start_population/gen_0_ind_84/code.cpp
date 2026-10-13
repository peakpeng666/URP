#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility> // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentClusterMembers;

    int numCustomersToRemove = getRandomNumber(15, 30);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    currentClusterMembers.push_back(seedCustomer);

    int expandFromIndex = 0;
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (expandFromIndex >= currentClusterMembers.size()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(newSeed) && selectedCustomersSet.size() < sol.instance.numCustomers) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            if (selectedCustomersSet.count(newSeed)) {
                break; // All customers are selected, or no new unique seed found
            }
            selectedCustomersSet.insert(newSeed);
            currentClusterMembers.push_back(newSeed);
            expandFromIndex = currentClusterMembers.size() - 1;
        }

        int customerToExpandFrom = currentClusterMembers[expandFromIndex];
        bool customerAddedThisIteration = false;

        int numNeighborsToCheck = std::min((int)sol.instance.adj[customerToExpandFrom].size(), getRandomNumber(5, 15));
        std::vector<int> potentialNeighbors;
        for (int i = 0; i < numNeighborsToCheck; ++i) {
            int neighbor = sol.instance.adj[customerToExpandFrom][i];
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                potentialNeighbors.push_back(neighbor);
            }
        }

        if (!potentialNeighbors.empty()) {
            int customerToAdd = potentialNeighbors[getRandomNumber(0, potentialNeighbors.size() - 1)];
            selectedCustomersSet.insert(customerToAdd);
            currentClusterMembers.push_back(customerToAdd);
            customerAddedThisIteration = true;
        }

        if (!customerAddedThisIteration) {
            expandFromIndex++;
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float twWidth = instance.TW_Width[customerId];
        float noise = getRandomFraction(-0.01f, 0.01f);
        customerScores.push_back({twWidth + noise, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}