#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomersToRemove = getRandomNumber(10, 20); 

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        int expandFromCustomerIdx = getRandomNumber(0, selectedCustomersVec.size() - 1);
        int currentSeed = selectedCustomersVec[expandFromCustomerIdx];

        std::vector<std::pair<float, int>> potentialNeighbors;
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                potentialNeighbors.push_back({sol.instance.distanceMatrix[currentSeed][i], i});
            }
        }

        if (potentialNeighbors.empty()) {
            break; 
        }

        std::sort(potentialNeighbors.begin(), potentialNeighbors.end());

        int poolSize = std::min((int)potentialNeighbors.size(), getRandomNumber(3, 8));
        
        int chosenIdxInPool = getRandomNumber(0, poolSize - 1);
        int newCustomer = potentialNeighbors[chosenIdxInPool].second;

        selectedCustomersSet.insert(newCustomer);
        selectedCustomersVec.push_back(newCustomer);
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerIdx : customers) {
        float score = 0.0f;

        if (instance.TW_Width[customerIdx] > 1e-3f) { 
            score += 100.0f / instance.TW_Width[customerIdx];
        } else {
            score += 10000.0f; 
        }

        score += 50.0f * instance.serviceTime[customerIdx];

        score += getRandomFractionFast() * 10.0f;

        scoredCustomers.push_back({score, customerIdx});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}