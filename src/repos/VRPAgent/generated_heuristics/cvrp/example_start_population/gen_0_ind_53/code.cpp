#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::min
#include <limits>    // For std::numeric_limits
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> customersToExplore;

    int numCustomersToRemove = getRandomNumber(15, 35);

    if (numCustomersToRemove == 0) {
        numCustomersToRemove = 1;
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    customersToExplore.push_back(seedCustomer);

    int head = 0;

    while (selectedCustomersSet.size() < numCustomersToRemove && head < customersToExplore.size()) {
        int currentCustomer = customersToExplore[head++];

        const auto& neighbors = sol.instance.adj[currentCustomer];
        
        int numNeighborsToTry = getRandomNumber(1, std::min((int)neighbors.size(), 5));

        for (int i = 0; i < numNeighborsToTry; ++i) {
            int neighborIdx = i;
            if (neighborIdx >= neighbors.size()) {
                break;
            }
            int neighbor = neighbors[neighborIdx];

            if (neighbor == 0 || selectedCustomersSet.count(neighbor)) {
                continue;
            }

            if (getRandomFractionFast() < 0.7) {
                selectedCustomersSet.insert(neighbor);
                customersToExplore.push_back(neighbor);

                if (selectedCustomersSet.size() == numCustomersToRemove) {
                    break;
                }
            }
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomersSet.insert(randomCustomer);
    }
    
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::unordered_set<int> remainingCustomersSet(customers.begin(), customers.end());
    std::vector<int> sortedCustomers;
    sortedCustomers.reserve(customers.size());

    int currentCustomerIndex = getRandomNumber(0, customers.size() - 1);
    int currentCustomer = customers[currentCustomerIndex];

    sortedCustomers.push_back(currentCustomer);
    remainingCustomersSet.erase(currentCustomer);

    while (!remainingCustomersSet.empty()) {
        std::vector<int> candidateNeighbors;
        
        const auto& neighborsOfCurrent = instance.adj[currentCustomer];
        int neighborsChecked = 0;
        int maxCandidatesToPool = 5;

        for (int neighbor : neighborsOfCurrent) {
            if (remainingCustomersSet.count(neighbor)) {
                candidateNeighbors.push_back(neighbor);
                neighborsChecked++;
                if (neighborsChecked >= maxCandidatesToPool) {
                    break;
                }
            }
        }

        if (candidateNeighbors.empty()) {
            float minDistance = std::numeric_limits<float>::max();
            for (int cust_id : remainingCustomersSet) {
                float dist = instance.distanceMatrix[currentCustomer][cust_id];
                if (dist < minDistance) {
                    minDistance = dist;
                    candidateNeighbors.clear();
                    candidateNeighbors.push_back(cust_id);
                } else if (dist == minDistance) {
                    candidateNeighbors.push_back(cust_id);
                }
            }
        }
        
        int nextCustomer = candidateNeighbors[getRandomNumber(0, candidateNeighbors.size() - 1)];

        sortedCustomers.push_back(nextCustomer);
        remainingCustomersSet.erase(nextCustomer);
        currentCustomer = nextCustomer;
    }

    customers = sortedCustomers;
}