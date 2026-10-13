#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatePool;

    int numCustomersToRemove = getRandomNumber(10, 25);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeedCustomer);

    for (size_t i = 0; i < sol.instance.adj[initialSeedCustomer].size(); ++i) {
        int neighbor = sol.instance.adj[initialSeedCustomer][i];
        if (neighbor != 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
            candidatePool.push_back(neighbor);
            if (candidatePool.size() >= 5 && selectedCustomers.size() < numCustomersToRemove) {
                // Limit initial neighbors added to the candidate pool
                break;
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            const int max_attempts = sol.instance.numCustomers * 2; // Prevent infinite loop on edge cases

            while (selectedCustomers.count(newSeed) && attempts < max_attempts) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }

            if (selectedCustomers.count(newSeed) && attempts >= max_attempts) {
                break; // Could not find an unselected customer, stop adding
            }

            selectedCustomers.insert(newSeed);
            for (size_t i = 0; i < sol.instance.adj[newSeed].size(); ++i) {
                int neighbor = sol.instance.adj[newSeed][i];
                if (neighbor != 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    candidatePool.push_back(neighbor);
                    if (candidatePool.size() >= 5 && selectedCustomers.size() < numCustomersToRemove) {
                        break;
                    }
                }
            }
            if (selectedCustomers.size() >= numCustomersToRemove) {
                break;
            }
            continue;
        }

        int idx = getRandomNumber(0, candidatePool.size() - 1);
        int customerToAdd = candidatePool[idx];

        std::swap(candidatePool[idx], candidatePool.back());
        candidatePool.pop_back();

        if (selectedCustomers.count(customerToAdd)) {
            continue;
        }

        selectedCustomers.insert(customerToAdd);

        for (size_t i = 0; i < sol.instance.adj[customerToAdd].size(); ++i) {
            int neighbor = sol.instance.adj[customerToAdd][i];
            if (neighbor != 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                candidatePool.push_back(neighbor);
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float selectionRand = getRandomFractionFast();

    if (selectionRand < 0.4) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] > instance.distanceMatrix[0][b];
        });
    } else if (selectionRand < 0.8) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] > instance.demand[b];
        });
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}