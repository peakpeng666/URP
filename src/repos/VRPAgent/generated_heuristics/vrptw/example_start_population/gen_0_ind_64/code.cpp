#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selectedCustomers;
    std::unordered_set<int> selectedSet;

    int numCustomersToRemove = getRandomNumber(8, 25); 

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    selectedCustomers.reserve(numCustomersToRemove);

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.push_back(initialCustomer);
    selectedSet.insert(initialCustomer);

    for (int i = 1; i < numCustomersToRemove; ++i) {
        int pivotCustomerIdx = getRandomNumber(0, selectedCustomers.size() - 1);
        int pivotCustomer = selectedCustomers[pivotCustomerIdx];

        std::vector<std::pair<float, int>> candidatesWithScores;
        candidatesWithScores.reserve(sol.instance.numCustomers - selectedSet.size());

        for (int cust_idx = 1; cust_idx <= sol.instance.numCustomers; ++cust_idx) {
            if (selectedSet.find(cust_idx) == selectedSet.end()) {
                float distance = sol.instance.distanceMatrix[cust_idx][pivotCustomer];
                float score = distance;

                if (sol.customerToTourMap[cust_idx] != sol.customerToTourMap[pivotCustomer]) {
                    score *= getRandomFraction(1.5f, 2.5f);
                }
                
                score *= getRandomFraction(0.9f, 1.1f);
                
                candidatesWithScores.push_back({score, cust_idx});
            }
        }

        if (candidatesWithScores.empty()) {
            break;
        }

        std::sort(candidatesWithScores.begin(), candidatesWithScores.end());

        int poolSize = getRandomNumber(3, 10);
        poolSize = std::min((int)candidatesWithScores.size(), poolSize);

        int chosenIdxInPool = getRandomNumber(0, poolSize - 1);
        int nextCustomer = candidatesWithScores[chosenIdxInPool].second;

        selectedCustomers.push_back(nextCustomer);
        selectedSet.insert(nextCustomer);
    }

    return selectedCustomers;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerId : customers) {
        float score = instance.TW_Width[customerId];

        score -= instance.demand[customerId] * getRandomFraction(0.0005f, 0.0015f); 
        score -= instance.serviceTime[customerId] * getRandomFraction(0.0005f, 0.0015f);

        score += getRandomFraction(-0.05f, 0.05f);

        scoredCustomers.push_back({score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}