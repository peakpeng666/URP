#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(static_cast<int>(0.02 * sol.instance.numCustomers), static_cast<int>(0.05 * sol.instance.numCustomers));
    if (numCustomersToRemove < 5) numCustomersToRemove = 5;
    if (numCustomersToRemove > 30) numCustomersToRemove = 30;

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesForGrowthPool;
    std::unordered_set<int> candidatesForGrowthSet;

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    candidatesForGrowthPool.push_back(initialCustomer);
    candidatesForGrowthSet.insert(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesForGrowthPool.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(newSeed)) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newSeed);
            candidatesForGrowthPool.push_back(newSeed);
            candidatesForGrowthSet.insert(newSeed);
            if (selectedCustomersSet.size() >= numCustomersToRemove) break;
        }

        int pivotIdx = getRandomNumber(0, candidatesForGrowthPool.size() - 1);
        int pivotCustomer = candidatesForGrowthPool[pivotIdx];
        
        candidatesForGrowthPool[pivotIdx] = candidatesForGrowthPool.back();
        candidatesForGrowthPool.pop_back();
        candidatesForGrowthSet.erase(pivotCustomer);

        const auto& neighbors = sol.instance.adj[pivotCustomer];
        std::vector<int> validNeighborsToAdd;
        int neighborsToCheckLimit = std::min((int)neighbors.size(), getRandomNumber(5, 15)); 

        for (int i = 0; i < neighborsToCheckLimit; ++i) {
            int neighbor = neighbors[i];
            if (!selectedCustomersSet.count(neighbor) && neighbor != 0) {
                validNeighborsToAdd.push_back(neighbor);
            }
        }

        if (!validNeighborsToAdd.empty()) {
            int chosenNeighbor = validNeighborsToAdd[getRandomNumber(0, validNeighborsToAdd.size() - 1)];
            selectedCustomersSet.insert(chosenNeighbor);
            if (!candidatesForGrowthSet.count(chosenNeighbor)) {
                candidatesForGrowthPool.push_back(chosenNeighbor);
                candidatesForGrowthSet.insert(chosenNeighbor);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    int choice = getRandomNumber(0, 4);

    std::vector<std::pair<float, int>> customerMetrics;

    for (int customerId : customers) {
        float metricValue;
        switch (choice) {
            case 0: 
                metricValue = instance.TW_Width[customerId];
                break;
            case 1: 
                metricValue = instance.startTW[customerId];
                break;
            case 2: 
                metricValue = -static_cast<float>(instance.demand[customerId]);
                break;
            case 3: 
                metricValue = -instance.serviceTime[customerId];
                break;
            case 4: 
                metricValue = -instance.distanceMatrix[0][customerId];
                break;
        }
        metricValue += getRandomFraction(-0.001f, 0.001f); 
        customerMetrics.push_back({metricValue, customerId});
    }

    std::sort(customerMetrics.begin(), customerMetrics.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerMetrics[i].second;
    }
}