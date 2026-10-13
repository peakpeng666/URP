#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::max/min
#include <vector> // For std::vector
#include "Utils.h" // For getRandomNumber, getRandomFractionFast, etc.

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomers = sol.instance.numCustomers;
    int minRemove = std::max(1, numCustomers / 100); 
    int maxRemove = std::min(numCustomers, numCustomers / 20);

    if (minRemove > maxRemove) {
        maxRemove = minRemove;
    }

    int numCustomersToRemove = getRandomNumber(minRemove, maxRemove);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    selectedCustomersVec.push_back(initialSeedCustomer);

    std::vector<int> expansionCandidates;
    expansionCandidates.push_back(initialSeedCustomer);

    int currentCustomersSelected = 1;

    while (currentCustomersSelected < numCustomersToRemove) {
        if (expansionCandidates.empty()) {
            int newRandomCustomer = getRandomNumber(1, numCustomers);
            while (selectedCustomersSet.count(newRandomCustomer)) {
                newRandomCustomer = getRandomNumber(1, numCustomers);
            }
            selectedCustomersSet.insert(newRandomCustomer);
            selectedCustomersVec.push_back(newRandomCustomer);
            expansionCandidates.push_back(newRandomCustomer);
            currentCustomersSelected++;
            if (currentCustomersSelected == numCustomersToRemove) break;
            continue;
        }

        int rand_idx = getRandomNumber(0, expansionCandidates.size() - 1);
        int current_customer_to_expand = expansionCandidates[rand_idx];

        bool neighborFound = false;
        for (int neighbor_id : sol.instance.adj[current_customer_to_expand]) {
            if (neighbor_id == 0) continue;
            if (selectedCustomersSet.count(neighbor_id) == 0) {
                selectedCustomersSet.insert(neighbor_id);
                selectedCustomersVec.push_back(neighbor_id);
                expansionCandidates.push_back(neighbor_id);
                currentCustomersSelected++;
                neighborFound = true;
                break;
            }
        }

        if (!neighborFound) {
            expansionCandidates.erase(expansionCandidates.begin() + rand_idx);
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::sort(customers.begin(), customers.end(), [&](int c1_idx, int c2_idx) {
        int demand1 = instance.demand[c1_idx];
        int demand2 = instance.demand[c2_idx];

        float random_factor = getRandomFractionFast();

        float stochastic_threshold = 0.15f; 
        if (random_factor < stochastic_threshold) {
            return getRandomFractionFast() < 0.5f; 
        } else {
            if (demand1 != demand2) {
                return demand1 > demand2;
            } else {
                float dist1 = instance.distanceMatrix[0][c1_idx];
                float dist2 = instance.distanceMatrix[0][c2_idx];
                return dist1 > dist2; 
            }
        }
    });
}