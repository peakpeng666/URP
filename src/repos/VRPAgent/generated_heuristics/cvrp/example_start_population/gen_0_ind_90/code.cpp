#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> neighborhoodExpansionQueue;

    int numCustomersToRemove = getRandomNumber(10, 20);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialCustomer);
    neighborhoodExpansionQueue.push_back(initialCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (neighborhoodExpansionQueue.empty()) {
            int newSeedCustomer = -1;
            int attempts = 0;
            const int max_attempts = sol.instance.numCustomers * 2;

            while (newSeedCustomer == -1 || selectedCustomers.count(newSeedCustomer) > 0) {
                newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
                if (attempts > max_attempts) {
                    break;
                }
            }
            if (selectedCustomers.count(newSeedCustomer) == 0) {
                selectedCustomers.insert(newSeedCustomer);
                neighborhoodExpansionQueue.push_back(newSeedCustomer);
            }
            if (selectedCustomers.size() >= numCustomersToRemove) break;
        }

        int currentSeedCustomerIdx = getRandomNumber(0, neighborhoodExpansionQueue.size() - 1);
        int currentSeedCustomer = neighborhoodExpansionQueue[currentSeedCustomerIdx];

        std::vector<int> potentialNeighbors;
        for (int neighbor : sol.instance.adj[currentSeedCustomer]) {
            if (neighbor == 0) continue;
            if (selectedCustomers.count(neighbor) == 0) {
                potentialNeighbors.push_back(neighbor);
            }
        }

        if (!potentialNeighbors.empty()) {
            int nextCustomer = potentialNeighbors[getRandomNumber(0, potentialNeighbors.size() - 1)];
            selectedCustomers.insert(nextCustomer);
            neighborhoodExpansionQueue.push_back(nextCustomer);
        } else {
            neighborhoodExpansionQueue[currentSeedCustomerIdx] = neighborhoodExpansionQueue.back();
            neighborhoodExpansionQueue.pop_back();
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::sort(customers.begin(), customers.end(), [&](int a, int b) {
        float scoreA = static_cast<float>(instance.demand[a]) + instance.distanceMatrix[0][a] * 0.01f;
        scoreA *= (1.0f + (getRandomFractionFast() - 0.5f) * 0.1f);

        float scoreB = static_cast<float>(instance.demand[b]) + instance.distanceMatrix[0][b] * 0.01f;
        scoreB *= (1.0f + (getRandomFractionFast() - 0.5f) * 0.1f);

        return scoreA > scoreB;
    });
}