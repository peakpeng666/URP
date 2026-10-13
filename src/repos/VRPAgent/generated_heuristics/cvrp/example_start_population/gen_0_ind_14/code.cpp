#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 20;
    
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    std::vector<int> candidateCustomersVec;
    std::unordered_set<int> candidateCustomersSet;

    int initialSeed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeed);
    selectedCustomersVec.push_back(initialSeed);

    const int numNeighborsToProbe = 5;
    int neighborsAdded = 0;
    for (int neighbor : sol.instance.adj[initialSeed]) {
        if (neighbor == 0) continue;
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() &&
            candidateCustomersSet.find(neighbor) == candidateCustomersSet.end()) {
            candidateCustomersVec.push_back(neighbor);
            candidateCustomersSet.insert(neighbor);
        }
        neighborsAdded++;
        if (neighborsAdded >= numNeighborsToProbe) break;
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int customerToSelect = -1;

        if (candidateCustomersVec.empty()) {
            int attempts = 0;
            const int maxAttempts = sol.instance.numCustomers * 2;
            while (customerToSelect == -1 && attempts < maxAttempts) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                    customerToSelect = randomCustomer;
                }
                attempts++;
            }
            if (customerToSelect == -1) {
                break;
            }
        } else {
            int randomIndex = getRandomNumber(0, candidateCustomersVec.size() - 1);
            customerToSelect = candidateCustomersVec[randomIndex];

            candidateCustomersVec[randomIndex] = candidateCustomersVec.back();
            candidateCustomersVec.pop_back();
            candidateCustomersSet.erase(customerToSelect);
        }

        selectedCustomersSet.insert(customerToSelect);
        selectedCustomersVec.push_back(customerToSelect);

        neighborsAdded = 0;
        for (int neighbor : sol.instance.adj[customerToSelect]) {
            if (neighbor == 0) continue;
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() &&
                candidateCustomersSet.find(neighbor) == candidateCustomersSet.end()) {
                candidateCustomersVec.push_back(neighbor);
                candidateCustomersSet.insert(neighbor);
            }
            neighborsAdded++;
            if (neighborsAdded >= numNeighborsToProbe) break;
        }
    }
    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;

    for (int customer_id : customers) {
        float total_dist_to_others = 0.0f;
        int count_others = 0;
        for (int other_customer_id : customers) {
            if (customer_id != other_customer_id) {
                total_dist_to_others += instance.distanceMatrix[customer_id][other_customer_id];
                count_others++;
            }
        }
        float average_dist = (count_others > 0) ? total_dist_to_others / count_others : 0.0f;

        average_dist += getRandomFractionFast() * 0.001f;

        scoredCustomers.push_back({average_dist, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}