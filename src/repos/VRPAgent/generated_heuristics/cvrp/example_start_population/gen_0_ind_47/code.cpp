#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesForExpansion;

    int numCustomersToRemove = getRandomNumber(10, 20);

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    candidatesForExpansion.push_back(seedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesForExpansion.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(newSeed)) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newSeed);
            candidatesForExpansion.push_back(newSeed);
            if (selectedCustomersSet.size() == numCustomersToRemove) break;
        }

        int currentCustomerIdx = getRandomNumber(0, candidatesForExpansion.size() - 1);
        int currentCustomer = candidatesForExpansion[currentCustomerIdx];

        bool neighborFound = false;
        
        const int numCloseNeighborsConsidered = std::min((int)sol.instance.adj[currentCustomer].size(), 5);
        if (numCloseNeighborsConsidered > 0) {
            std::vector<int> potentialNeighbors;
            for (int i = 0; i < numCloseNeighborsConsidered; ++i) {
                int neighbor = sol.instance.adj[currentCustomer][i];
                if (neighbor != 0 && selectedCustomersSet.count(neighbor) == 0) {
                    potentialNeighbors.push_back(neighbor);
                }
            }

            if (!potentialNeighbors.empty()) {
                int selectedNeighbor = potentialNeighbors[getRandomNumber(0, potentialNeighbors.size() - 1)];
                selectedCustomersSet.insert(selectedNeighbor);
                candidatesForExpansion.push_back(selectedNeighbor);
                neighborFound = true;
            }
        }
        
        if (selectedCustomersSet.size() == numCustomersToRemove) break;

        if (!neighborFound) {
            if (!candidatesForExpansion.empty()) {
                candidatesForExpansion[currentCustomerIdx] = candidatesForExpansion.back();
                candidatesForExpansion.pop_back();
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float randomPerturbationFactor = 0.05f;

    int sortingCriterionChoice = getRandomNumber(0, 2);

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = 0.0f;
        float demand = static_cast<float>(instance.demand[customerId]);
        float distToDepot = instance.distanceMatrix[0][customerId];

        if (sortingCriterionChoice == 0) {
            score = -demand;
        } else if (sortingCriterionChoice == 1) {
            score = -distToDepot;
        } else {
            score = distToDepot;
        }

        score += getRandomFractionFast() * randomPerturbationFactor;
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first < b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}