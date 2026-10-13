#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 25);
    std::vector<int> customersToRemove;
    customersToRemove.reserve(numCustomersToRemove);

    std::unordered_set<int> removedSet;

    std::vector<int> expansionCandidates;
    std::unordered_set<int> expansionCandidatesSet;

    int initialSeed = getRandomNumber(1, sol.instance.numCustomers);
    customersToRemove.push_back(initialSeed);
    removedSet.insert(initialSeed);
    expansionCandidates.push_back(initialSeed);
    expansionCandidatesSet.insert(initialSeed);

    while (customersToRemove.size() < numCustomersToRemove) {
        int currentSourceCustomer = -1;

        if (!expansionCandidates.empty()) {
            int candidateIdx = getRandomNumber(0, expansionCandidates.size() - 1);
            currentSourceCustomer = expansionCandidates[candidateIdx];

            expansionCandidates[candidateIdx] = expansionCandidates.back();
            expansionCandidates.pop_back();
            expansionCandidatesSet.erase(currentSourceCustomer);
        } else {
            currentSourceCustomer = getRandomNumber(1, sol.instance.numCustomers);
        }

        bool addedNeighbor = false;
        for (int neighborId : sol.instance.adj[currentSourceCustomer]) {
            if (neighborId > 0 && removedSet.find(neighborId) == removedSet.end()) {
                customersToRemove.push_back(neighborId);
                removedSet.insert(neighborId);

                expansionCandidates.push_back(neighborId);
                expansionCandidatesSet.insert(neighborId);
                addedNeighbor = true;
                break;
            }
        }
    }

    return customersToRemove;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int strategy = getRandomNumber(0, 3);

    if (strategy == 0) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] > instance.demand[b];
        });
    } else if (strategy == 1) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
        });
    } else if (strategy == 2) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] > instance.distanceMatrix[0][b];
        });
    } else if (strategy == 3) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.adj[a].size() > instance.adj[b].size();
        });
    }

    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFractionFast() < 0.1) {
            std::swap(customers[i], customers[i + 1]);
        }
    }
}