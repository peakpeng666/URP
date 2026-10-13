#include "AgentDesigned.h" // Assuming this includes Solution.h, Instance.h, Tour.h
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle
#include <vector>
#include <cmath> // For std::sqrt, std::pow (if using Euclidean distance directly, though distanceMatrix is provided)
#include "Utils.h" // For getRandomNumber, getRandomFraction, argsort

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> removedCustomersSet;
    std::vector<int> candidateCustomers;

    const int minCustomersToRemove = 10;
    const int maxCustomersToRemove = 40;
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    if (numCustomersToRemove <= 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    removedCustomersSet.insert(initialCustomer);
    candidateCustomers.push_back(initialCustomer);

    while (removedCustomersSet.size() < numCustomersToRemove) {
        if (candidateCustomers.empty()) {
            int newSeedCustomer = -1;
            int attempts = 0;
            const int maxAttempts = sol.instance.numCustomers * 2;
            while (newSeedCustomer == -1 && attempts < maxAttempts) {
                int potentialCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (removedCustomersSet.find(potentialCustomer) == removedCustomersSet.end()) {
                    newSeedCustomer = potentialCustomer;
                }
                attempts++;
            }
            if (newSeedCustomer == -1) {
                break;
            }
            removedCustomersSet.insert(newSeedCustomer);
            candidateCustomers.push_back(newSeedCustomer);
        }

        int candidateIdx = getRandomNumber(0, candidateCustomers.size() - 1);
        int currentCustomer = candidateCustomers[candidateIdx];

        std::swap(candidateCustomers[candidateIdx], candidateCustomers.back());
        candidateCustomers.pop_back();

        const int numNeighborsToConsider = std::min((int)sol.instance.adj[currentCustomer].size(), 10);

        std::vector<int> eligibleNeighbors;
        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[currentCustomer][i];
            if (neighbor != 0 && removedCustomersSet.find(neighbor) == removedCustomersSet.end()) {
                eligibleNeighbors.push_back(neighbor);
            }
        }

        if (!eligibleNeighbors.empty()) {
            int chosenNeighbor = eligibleNeighbors[getRandomNumber(0, eligibleNeighbors.size() - 1)];
            removedCustomersSet.insert(chosenNeighbor);
            candidateCustomers.push_back(chosenNeighbor);
        }
    }

    return std::vector<int>(removedCustomersSet.begin(), removedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<float> scores(customers.size());

    const float demandWeight = 1.0f;
    const float distanceWeight = 0.5f;
    const float perturbationScale = 0.01f;

    for (size_t i = 0; i < customers.size(); ++i) {
        int customerId = customers[i];
        float customerDemand = static_cast<float>(instance.demand[customerId]);
        float distanceFromDepot = instance.distanceMatrix[0][customerId];

        scores[i] = (demandWeight * customerDemand) +
                    (distanceWeight * distanceFromDepot) +
                    (getRandomFractionFast() * perturbationScale);
    }

    std::vector<int> sortedIndices = argsort(scores);

    std::vector<int> sortedCustomers(customers.size());
    for (size_t i = 0; i < customers.size(); ++i) {
        sortedCustomers[i] = customers[sortedIndices[customers.size() - 1 - i]];
    }
    customers = sortedCustomers;
}