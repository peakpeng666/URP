#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;

    int minCustomersToRemove = std::max(10, static_cast<int>(sol.instance.numCustomers * 0.02));
    int maxCustomersToRemove = std::min(20, static_cast<int>(sol.instance.numCustomers * 0.04));
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) numCustomersToRemove = 1;

    if (numCustomersToRemove == 0) { // Case for extremely small instances where no customers can be removed
        return {};
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialCustomer);
    std::vector<int> currentClusterNodes = {initialCustomer};

    while (selectedCustomers.size() < numCustomersToRemove) {
        int pivotIndex = getRandomNumber(0, currentClusterNodes.size() - 1);
        int pivotCustomer = currentClusterNodes[pivotIndex];

        std::vector<int> candidatesForNext;
        int maxNeighborsToScan = std::min(static_cast<int>(sol.instance.adj[pivotCustomer].size()), 20); 

        for (int i = 0; i < maxNeighborsToScan; ++i) {
            int neighborId = sol.instance.adj[pivotCustomer][i];
            if (neighborId == 0) continue;
            if (selectedCustomers.find(neighborId) == selectedCustomers.end()) {
                candidatesForNext.push_back(neighborId);
            }
        }

        int newCustomer = -1;
        if (!candidatesForNext.empty()) {
            newCustomer = candidatesForNext[getRandomNumber(0, candidatesForNext.size() - 1)];
        } else {
            do {
                newCustomer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomers.count(newCustomer) && selectedCustomers.size() < sol.instance.numCustomers);

            if (selectedCustomers.count(newCustomer)) { 
                break; // All customers are already selected, cannot add more
            }
        }
        
        selectedCustomers.insert(newCustomer);
        currentClusterNodes.push_back(newCustomer);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    int sortingCriterion = getRandomNumber(0, 4);

    for (int customerId : customers) {
        float score = 0.0f;
        float demand = static_cast<float>(instance.demand[customerId]);
        float distToDepot = instance.distanceMatrix[0][customerId];

        if (sortingCriterion == 0) { 
            score = demand;
        } else if (sortingCriterion == 1) {
            score = distToDepot;
        } else if (sortingCriterion == 2) {
            score = (demand > 0) ? (1.0f / demand) : std::numeric_limits<float>::max();
        } else if (sortingCriterion == 3) {
            score = (distToDepot > 0) ? (1.0f / distToDepot) : std::numeric_limits<float>::max();
        } else { 
            score = demand + distToDepot;
        }
        
        score += getRandomFractionFast() * 0.001f;

        customerScores.push_back({score, customerId});
    }

    if (getRandomFractionFast() < 0.5f) {
        std::sort(customerScores.begin(), customerScores.end());
    } else {
        std::sort(customerScores.rbegin(), customerScores.rend());
    }

    for (size_t i = 0; i < customerScores.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}