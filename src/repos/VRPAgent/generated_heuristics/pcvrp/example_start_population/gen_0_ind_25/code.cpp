#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <numeric>

// Forward declarations for utility functions assumed to be in Utils.h
// int getRandomNumber(int min, int max);
// float getRandomFraction(float min = 0.0, float max = 1.0);
// float getRandomFractionFast();

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> customersToExplore;

    int numCustomersToRemove = getRandomNumber(10, 20); 
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        return {};
    }

    int numInitialSeeds = getRandomNumber(1, 3);
    for (int i = 0; i < numInitialSeeds && selectedCustomersSet.size() < numCustomersToRemove; ++i) {
        int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomersSet.insert(seedCustomer).second) {
            customersToExplore.push_back(seedCustomer);
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (customersToExplore.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.insert(newSeed).second) {
                customersToExplore.push_back(newSeed);
            }
            continue;
        }

        int randIdxInExplorePool = getRandomNumber(0, (int)customersToExplore.size() - 1);
        int currentCustomer = customersToExplore[randIdxInExplorePool];

        const auto& neighbors = sol.instance.adj[currentCustomer];
        if (neighbors.empty()) {
            customersToExplore.erase(customersToExplore.begin() + randIdxInExplorePool);
            continue;
        }

        int numNeighborsToConsider = std::min((int)neighbors.size(), 10);
        if (numNeighborsToConsider == 0) {
             customersToExplore.erase(customersToExplore.begin() + randIdxInExplorePool);
             continue;
        }
        int neighborIdxInAdj = getRandomNumber(0, numNeighborsToConsider - 1);
        int candidateNeighbor = neighbors[neighborIdxInAdj];

        if (selectedCustomersSet.insert(candidateNeighbor).second) {
            customersToExplore.push_back(candidateNeighbor);
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = 0.0;

        float customerPrize = instance.prizes[customerId];
        float customerDemand = instance.demand[customerId];
        
        if (customerDemand > 0) {
            score += 100.0 * (customerPrize / customerDemand);
        } else {
            score += 100.0 * customerPrize;
        }

        score += 0.5 * instance.adj[customerId].size();

        score -= 0.1 * instance.distanceMatrix[0][customerId];

        score += getRandomFraction(-0.01, 0.01); 

        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}