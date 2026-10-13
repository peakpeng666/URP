#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;
    std::vector<int> candidateCustomers;
    std::unordered_set<int> candidateSet;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 20;
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);
    int numNeighborsToAdd = 5;

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    int neighborsAddedCount = 0;
    for (int neighbor : sol.instance.adj[initialCustomer]) {
        if (neighbor == 0) continue;
        if (neighbor < 1 || neighbor > sol.instance.numCustomers) continue;

        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            if (candidateSet.find(neighbor) == candidateSet.end()) {
                candidateCustomers.push_back(neighbor);
                candidateSet.insert(neighbor);
                neighborsAddedCount++;
                if (neighborsAddedCount >= numNeighborsToAdd) break;
            }
        }
    }

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        int chosenCustomer = -1;
        if (!candidateCustomers.empty()) {
            int idx = getRandomNumber(0, candidateCustomers.size() - 1);
            chosenCustomer = candidateCustomers[idx];

            candidateCustomers[idx] = candidateCustomers.back();
            candidateCustomers.pop_back();
            candidateSet.erase(chosenCustomer);
        } else {
            int attempts = sol.instance.numCustomers * 2;
            for (int i = 0; i < attempts; ++i) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                    chosenCustomer = randomCustomer;
                    break;
                }
            }
            if (chosenCustomer == -1) {
                break;
            }
        }

        if (selectedCustomersSet.find(chosenCustomer) != selectedCustomersSet.end()) {
            continue;
        }

        selectedCustomersSet.insert(chosenCustomer);
        selectedCustomersVec.push_back(chosenCustomer);

        neighborsAddedCount = 0;
        for (int neighbor : sol.instance.adj[chosenCustomer]) {
            if (neighbor == 0) continue;
            if (neighbor < 1 || neighbor > sol.instance.numCustomers) continue;

            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (candidateSet.find(neighbor) == candidateSet.end()) {
                    candidateCustomers.push_back(neighbor);
                    candidateSet.insert(neighbor);
                    neighborsAddedCount++;
                    if (neighborsAddedCount >= numNeighborsToAdd) break;
                }
            }
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int strategy_choice = getRandomNumber(0, 2);

    if (strategy_choice == 0) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] > instance.distanceMatrix[0][c2];
        });
    } else if (strategy_choice == 1) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.demand[c1] > instance.demand[c2];
        });
    } else {
        float max_dist = 0.0f;
        for (int cust_idx : customers) {
            if (instance.distanceMatrix[0][cust_idx] > max_dist) {
                max_dist = instance.distanceMatrix[0][cust_idx];
            }
        }
        
        float noise_amplitude = max_dist * 0.1f; 

        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float noise1 = (getRandomFractionFast() - 0.5f) * noise_amplitude;
            float noise2 = (getRandomFractionFast() - 0.5f) * noise_amplitude;

            float score1 = instance.distanceMatrix[0][c1] + noise1;
            float score2 = instance.distanceMatrix[0][c2] + noise2;
            return score1 > score2;
        });
    }
}