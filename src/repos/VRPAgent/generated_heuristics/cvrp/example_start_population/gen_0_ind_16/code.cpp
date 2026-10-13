#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort, std::min, std::max
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomersToRemove = getRandomNumber(10, 30);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    if (numCustomersToRemove == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        int candidateToAdd = -1;
        int maxRetries = 100;

        for (int retry = 0; retry < maxRetries; ++retry) {
            if (selectedCustomersVec.empty()) break; 

            int pivotCustomerIndex = getRandomNumber(0, selectedCustomersVec.size() - 1);
            int pivotCustomer = selectedCustomersVec[pivotCustomerIndex];

            const auto& neighbors = sol.instance.adj[pivotCustomer];
            if (neighbors.empty()) continue;

            int k = getRandomNumber(5, 10); 
            int neighborIdx = getRandomNumber(0, std::min((int)neighbors.size() - 1, k - 1));
            
            candidateToAdd = neighbors[neighborIdx];

            if (candidateToAdd != 0 && selectedCustomersSet.find(candidateToAdd) == selectedCustomersSet.end()) {
                break;
            } else {
                candidateToAdd = -1;
            }
        }

        if (candidateToAdd != -1) {
            selectedCustomersSet.insert(candidateToAdd);
            selectedCustomersVec.push_back(candidateToAdd);
        } else {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                 selectedCustomersSet.insert(randomCustomer);
                 selectedCustomersVec.push_back(randomCustomer);
            }
            if (selectedCustomersVec.size() == numCustomersToRemove) break;
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerDistances;
    customerDistances.reserve(customers.size());
    for (int customerId : customers) {
        customerDistances.push_back({instance.distanceMatrix[0][customerId], customerId});
    }

    std::sort(customerDistances.begin(), customerDistances.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customerDistances.size(); ++i) {
        if (getRandomNumber(0, 99) < 25) { 
            int shake_radius = getRandomNumber(2, 5); 
            
            int start_idx = std::max(0, (int)i - shake_radius);
            int end_idx = std::min((int)customerDistances.size() - 1, (int)i + shake_radius);
            
            if (start_idx >= end_idx) continue; 

            int j = getRandomNumber(start_idx, end_idx);
            
            std::swap(customerDistances[i], customerDistances[j]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerDistances[i].second;
    }
}