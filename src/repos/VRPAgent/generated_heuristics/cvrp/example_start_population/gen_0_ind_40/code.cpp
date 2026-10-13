#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomersToRemove = getRandomNumber(static_cast<int>(sol.instance.numCustomers * 0.02), static_cast<int>(sol.instance.numCustomers * 0.04));
    if (numCustomersToRemove < 5) numCustomersToRemove = 5;
    if (numCustomersToRemove > 20) numCustomersToRemove = 20;

    int seedCustomer = -1;
    if (!sol.tours.empty()) {
        int attemptCount = 0;
        int maxAttempts = 10;
        while (seedCustomer == -1 && attemptCount < maxAttempts) {
            int randomTourIdx = getRandomNumber(0, sol.tours.size() - 1);
            if (!sol.tours[randomTourIdx].customers.empty()) {
                seedCustomer = sol.tours[randomTourIdx].customers[getRandomNumber(0, sol.tours[randomTourIdx].customers.size() - 1)];
            }
            attemptCount++;
        }
    }

    if (seedCustomer == -1) {
        seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersList.push_back(seedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool addedNeighbor = false;
        int customerToExpandFrom = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];

        for (int neighborNodeId : sol.instance.adj[customerToExpandFrom + 1]) {
            if (neighborNodeId == 0) continue;
            int neighborCustomerId = neighborNodeId - 1;

            if (selectedCustomersSet.find(neighborCustomerId) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(neighborCustomerId);
                selectedCustomersList.push_back(neighborCustomerId);
                addedNeighbor = true;
                break;
            }
        }

        if (!addedNeighbor) {
            int randomCustomerId = getRandomNumber(1, sol.instance.numCustomers);
            int attemptLimit = 100;
            int currentAttempt = 0;
            while (selectedCustomersSet.find(randomCustomerId) != selectedCustomersSet.end() && currentAttempt < attemptLimit) {
                randomCustomerId = getRandomNumber(1, sol.instance.numCustomers);
                currentAttempt++;
            }
            if (selectedCustomersSet.find(randomCustomerId) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(randomCustomerId);
                selectedCustomersList.push_back(randomCustomerId);
            } else {
                break;
            }
        }
    }

    return selectedCustomersList;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<float> scores;
    scores.reserve(customers.size());

    for (int custId : customers) {
        float demand = static_cast<float>(instance.demand[custId]);
        float distFromDepot = instance.distanceMatrix[0][custId + 1];

        float score = demand * 1000.0f + distFromDepot * 1.0f + getRandomFractionFast() * 0.01f;
        
        scores.push_back(-score);
    }

    std::vector<int> sortedIndices = argsort(scores);

    std::vector<int> tempCustomers;
    tempCustomers.reserve(customers.size());

    for (int originalIdx : sortedIndices) {
        tempCustomers.push_back(customers[originalIdx]);
    }

    customers = tempCustomers;
}