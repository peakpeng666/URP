#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatesForExpansion;

    int minCustomersToRemove = std::max(5, (int)(sol.instance.numCustomers * 0.02));
    int maxCustomersToRemove = std::min(50, (int)(sol.instance.numCustomers * 0.04));
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialCustomer);
    candidatesForExpansion.push_back(initialCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidatesForExpansion.empty()) {
            int newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            while (selectedCustomers.count(newRandomCustomer) && attempts < 100) {
                newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (!selectedCustomers.count(newRandomCustomer)) {
                selectedCustomers.insert(newRandomCustomer);
                candidatesForExpansion.push_back(newRandomCustomer);
            } else {
                break;
            }
        }

        int anchorIdx = getRandomNumber(0, (int)candidatesForExpansion.size() - 1);
        int anchorCustomer = candidatesForExpansion[anchorIdx];

        bool foundNewCustomer = false;
        int numNeighborsToConsider = std::min((int)sol.instance.adj[anchorCustomer].size(), 10);

        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[anchorCustomer][i];
            if (neighbor > 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                if (getRandomFractionFast() < 0.7) { 
                    selectedCustomers.insert(neighbor);
                    candidatesForExpansion.push_back(neighbor);
                    foundNewCustomer = true;
                    break;
                }
            }
        }

        if (!foundNewCustomer) {
            std::swap(candidatesForExpansion[anchorIdx], candidatesForExpansion.back());
            candidatesForExpansion.pop_back();
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;

    for (int customer_id : customers) {
        float score = 0.0;
        
        score += instance.demand[customer_id] * 0.5; 
        score += instance.distanceMatrix[0][customer_id] * 0.5; 
        
        float noise_scale = (instance.vehicleCapacity / 10.0) + 10.0;
        score += getRandomFractionFast() * noise_scale;

        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.rbegin(), scoredCustomers.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}