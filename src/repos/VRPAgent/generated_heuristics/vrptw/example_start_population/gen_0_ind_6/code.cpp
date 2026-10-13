#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    int numCustomersToRemove = getRandomNumber(10, 25); 

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        std::vector<int> candidatePool;
        
        for (int currentSelectedCustomer : selectedCustomersSet) {
            const auto& neighbors = sol.instance.adj[currentSelectedCustomer];
            int neighborsToConsider = std::min((int)neighbors.size(), 15); 

            for (int i = 0; i < neighborsToConsider; ++i) {
                int neighbor = neighbors[i];
                if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && 
                    selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    candidatePool.push_back(neighbor);
                }
            }
        }

        if (!candidatePool.empty()) {
            int idx = getRandomNumber(0, candidatePool.size() - 1);
            selectedCustomersSet.insert(candidatePool[idx]);
        } else {
            int randomUnselectedCustomer;
            do {
                randomUnselectedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.count(randomUnselectedCustomer));
            selectedCustomersSet.insert(randomUnselectedCustomer);
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerData;
    customerData.reserve(customers.size());
    for (int customerId : customers) {
        customerData.push_back({instance.TW_Width[customerId], customerId});
    }

    std::sort(customerData.begin(), customerData.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first < b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerData[i].second;
    }

    float perturbationProbability = 0.20;
    int maxSwapDistance = 5;             

    for (size_t i = 0; i < customers.size(); ++i) {
        if (getRandomFraction() < perturbationProbability) {
            int potentialSwapIdx = i + getRandomNumber(1, maxSwapDistance);
            if (potentialSwapIdx < customers.size()) {
                std::swap(customers[i], customers[potentialSwapIdx]);
            }
        }
        if (getRandomFraction() < perturbationProbability * 0.5) {
            int potentialSwapIdx = i - getRandomNumber(1, maxSwapDistance);
            if (potentialSwapIdx >= 0) {
                std::swap(customers[i], customers[potentialSwapIdx]);
            }
        }
    }
}