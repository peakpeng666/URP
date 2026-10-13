#include "AgentDesigned.h"
#include <random> 
#include <unordered_set>
#include <algorithm> 
#include <vector>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove > instance.numCustomers) {
        numCustomersToRemove = instance.numCustomers;
    }
    if (numCustomersToRemove == 0 && instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    } else if (instance.numCustomers == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    selectedCustomersVec.push_back(initialSeedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int anchorCustomerIndex = getRandomNumber(0, (int)selectedCustomersVec.size() - 1);
        int anchorCustomer = selectedCustomersVec[anchorCustomerIndex];

        bool added_one = false;
        for (int neighborNode : instance.adj[anchorCustomer]) {
            if (neighborNode == 0) continue;

            if (neighborNode >= 1 && neighborNode <= instance.numCustomers && 
                selectedCustomersSet.find(neighborNode) == selectedCustomersSet.end()) {
                
                if (getRandomFractionFast() < 0.8f) {
                    selectedCustomersSet.insert(neighborNode);
                    selectedCustomersVec.push_back(neighborNode);
                    added_one = true;
                    break;
                }
            }
        }

        if (!added_one && selectedCustomersSet.size() < numCustomersToRemove) {
            int randomCustomerToAdd;
            do {
                randomCustomerToAdd = getRandomNumber(1, instance.numCustomers);
            } while (selectedCustomersSet.find(randomCustomerToAdd) != selectedCustomersSet.end());
            selectedCustomersSet.insert(randomCustomerToAdd);
            selectedCustomersVec.push_back(randomCustomerToAdd);
        }
    }
    return selectedCustomersVec;
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float distance_weight_factor = 0.05f; 

    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        float score1 = (float)instance.demand[c1] + distance_weight_factor * instance.distanceMatrix[c1][0];
        float score2 = (float)instance.demand[c2] + distance_weight_factor * instance.distanceMatrix[c2][0];

        if (getRandomFractionFast() < 0.15f) {
            return score1 < score2;
        } else {
            return score1 > score2;
        }
    });
}