#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomersToRemove = 10 + getRandomNumber(0, 20); 

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers); 
    
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersVec.push_back(seedCustomer);

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        int centerCustomerIdx = getRandomNumber(0, selectedCustomersVec.size() - 1);
        int centerCustomer = selectedCustomersVec[centerCustomerIdx];

        bool addedNewCustomer = false;
        for (int neighbor : sol.instance.adj[centerCustomer]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (getRandomFractionFast() < 0.1f) { 
                    continue; 
                }

                selectedCustomersSet.insert(neighbor);
                selectedCustomersVec.push_back(neighbor);
                addedNewCustomer = true;
                break;
            }
        }

        if (!addedNewCustomer) {
            // If all neighbors of the current centerCustomer are already selected,
            // the loop will naturally pick another centerCustomer in the next iteration.
            // This ensures the removal set continues to grow if possible.
        }
    }
    
    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float prize = instance.prizes[customerId];
        float distFromDepot = instance.distanceMatrix[0][customerId];

        if (distFromDepot < 0.1f) {
            distFromDepot = 0.1f; 
        }
        
        float score = prize / distFromDepot;
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }

    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFractionFast() < 0.05f) { 
            std::swap(customers[i], customers[i+1]);
        }
    }
}