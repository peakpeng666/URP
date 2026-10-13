#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"
#include "Solution.h"
#include "Instance.h"
#include "Tour.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedSet;
    std::vector<int> selectedList;

    int numCustomersToRemove = getRandomNumber(25, 45);

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedSet.insert(initialCustomer);
    selectedList.push_back(initialCustomer);

    while (selectedList.size() < numCustomersToRemove) {
        int baseCustomerIdx = getRandomNumber(0, selectedList.size() - 1);
        int baseCustomer = selectedList[baseCustomerIdx];

        int chosenNeighbor = -1;
        int maxNeighborsToConsider = std::min((int)sol.instance.adj[baseCustomer].size(), 100); 

        if (maxNeighborsToConsider > 0) {
            int startIdx = getRandomNumber(0, maxNeighborsToConsider - 1);
            for (int i = 0; i < maxNeighborsToConsider; ++i) {
                int neighborCustomer = sol.instance.adj[baseCustomer][(startIdx + i) % maxNeighborsToConsider];
                if (selectedSet.find(neighborCustomer) == selectedSet.end()) {
                    chosenNeighbor = neighborCustomer;
                    break;
                }
            }
        }

        if (chosenNeighbor != -1) {
            selectedList.push_back(chosenNeighbor);
            selectedSet.insert(chosenNeighbor);
        } else {
            int fallbackCustomer = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            const int maxFallbackAttempts = sol.instance.numCustomers * 2;
            while (selectedSet.count(fallbackCustomer) > 0 && attempts < maxFallbackAttempts) {
                fallbackCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            
            if (selectedSet.count(fallbackCustomer) == 0) {
                selectedList.push_back(fallbackCustomer);
                selectedSet.insert(fallbackCustomer);
            } else {
                break;
            }
        }
    }

    return selectedList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerId : customers) {
        float demandValue = static_cast<float>(instance.demand[customerId]);
        float distToDepot = instance.distanceMatrix[0][customerId];

        float score = demandValue * 1000.0f - distToDepot;

        score += (getRandomFractionFast() - 0.5f) * (demandValue + distToDepot) * 0.01f;

        scoredCustomers.push_back({score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}