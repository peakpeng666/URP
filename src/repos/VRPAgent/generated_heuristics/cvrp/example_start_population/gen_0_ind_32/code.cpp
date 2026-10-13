#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentExpansionFront;

    int numCustomersToRemove = getRandomNumber(10, 25);

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    currentExpansionFront.push_back(initialSeedCustomer);

    int head = 0; 

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (head >= currentExpansionFront.size()) {
            bool newSeedFound = false;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(i);
                    currentExpansionFront.push_back(i);
                    newSeedFound = true;
                    break;
                }
            }
            if (!newSeedFound) {
                break;
            }
        }

        int currentPivotCustomer = currentExpansionFront[head++];

        int numNeighborsToConsider = std::min((int)sol.instance.adj[currentPivotCustomer].size(), 5);

        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int neighborId = sol.instance.adj[currentPivotCustomer][i];

            if (neighborId > 0 && neighborId <= sol.instance.numCustomers && 
                selectedCustomersSet.find(neighborId) == selectedCustomersSet.end()) {
                
                if (getRandomFractionFast() < 0.7f) {
                    selectedCustomersSet.insert(neighborId);
                    currentExpansionFront.push_back(neighborId);

                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        break;
                    }
                }
            }
        }
        if (selectedCustomersSet.size() == numCustomersToRemove) {
            break;
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;

    for (int customerId : customers) {
        float distanceToDepot = instance.distanceMatrix[0][customerId];
        float demandFactor = (float)instance.demand[customerId] / instance.vehicleCapacity;
        
        float score = distanceToDepot + (demandFactor * 50.0f);
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i + 1 < customerScores.size(); ++i) {
        if (getRandomFractionFast() < 0.15f) {
            std::swap(customerScores[i], customerScores[i+1]);
        }
    }

    for (size_t i = 0; i < customerScores.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}