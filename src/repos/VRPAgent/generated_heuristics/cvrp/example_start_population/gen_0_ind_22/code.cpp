#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits>

// These functions are assumed to be provided by "Utils.h" as per the problem description.
// int getRandomNumber(int min, int max);
// float getRandomFractionFast();

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomers = sol.instance.numCustomers;
    int minCustomersToRemove = std::max(5, numCustomers / 50);
    int maxCustomersToRemove = std::min(30, numCustomers / 15);
    int numCustomersToSelect = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    std::vector<int> selectedCustomersVec;
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> expansionCandidates;

    if (numCustomersToSelect <= 0 || numCustomers == 0) {
        return selectedCustomersVec;
    }

    int seedCustomer = getRandomNumber(1, numCustomers);
    selectedCustomersVec.push_back(seedCustomer);
    selectedCustomersSet.insert(seedCustomer);
    expansionCandidates.push_back(seedCustomer);

    while (selectedCustomersVec.size() < numCustomersToSelect) {
        if (expansionCandidates.empty()) {
            int newSeed = getRandomNumber(1, numCustomers);
            while (selectedCustomersSet.count(newSeed) > 0 && selectedCustomersSet.size() < numCustomers) {
                newSeed = getRandomNumber(1, numCustomers);
            }
            if (selectedCustomersSet.count(newSeed) > 0) {
                break;
            }
            selectedCustomersVec.push_back(newSeed);
            selectedCustomersSet.insert(newSeed);
            expansionCandidates.push_back(newSeed);
            if (selectedCustomersVec.size() == numCustomersToSelect) {
                break;
            }
        }

        int candidateIdx = getRandomNumber(0, expansionCandidates.size() - 1);
        int currentCustomer = expansionCandidates[candidateIdx];
        expansionCandidates[candidateIdx] = expansionCandidates.back();
        expansionCandidates.pop_back();

        int neighborsToConsider = std::min((int)sol.instance.adj[currentCustomer].size(), 10);
        std::vector<int> potentialNewCustomers;
        for (int i = 0; i < neighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[currentCustomer][i];
            if (neighbor != 0 && selectedCustomersSet.count(neighbor) == 0) {
                potentialNewCustomers.push_back(neighbor);
            }
        }

        if (!potentialNewCustomers.empty()) {
            int newCustomerIdx = getRandomNumber(0, potentialNewCustomers.size() - 1);
            int newCustomer = potentialNewCustomers[newCustomerIdx];

            selectedCustomersVec.push_back(newCustomer);
            selectedCustomersSet.insert(newCustomer);
            expansionCandidates.push_back(newCustomer);
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float distanceToDepot = instance.distanceMatrix[0][customerId];
        
        float score = distanceToDepot + getRandomFractionFast() * 0.001f; 
        
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; 
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}