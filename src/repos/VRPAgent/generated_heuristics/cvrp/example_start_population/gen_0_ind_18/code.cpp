#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int minCustomersToRemove = 10;
    const int maxCustomersToRemove = 20;

    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool added_in_this_iteration = false;

        if (!selectedCustomersVec.empty()) {
            int pivotIndex = getRandomNumber(0, static_cast<int>(selectedCustomersVec.size()) - 1);
            int pivotCustomer = selectedCustomersVec[pivotIndex];

            int numNeighborsToCheck = std::min(static_cast<int>(sol.instance.adj[pivotCustomer].size()), 10);

            for (int i = 0; i < numNeighborsToCheck; ++i) {
                int neighbor = sol.instance.adj[pivotCustomer][i];

                if (neighbor == 0 || selectedCustomersSet.count(neighbor)) {
                    continue;
                }

                if (getRandomFractionFast() < 0.75) {
                    selectedCustomersSet.insert(neighbor);
                    selectedCustomersVec.push_back(neighbor);
                    added_in_this_iteration = true;
                    break;
                }
            }
        }

        if (!added_in_this_iteration) {
            int newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.count(newRandomCustomer) == 0) {
                selectedCustomersSet.insert(newRandomCustomer);
                selectedCustomersVec.push_back(newRandomCustomer);
            }
        }
    }
    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    const float demandWeight = 1.5;
    const float distanceWeight = 1.0;
    const float noiseMagnitude = 0.05;

    for (int customer_id : customers) {
        float score = 0.0;
        score += instance.demand[customer_id] * demandWeight;
        score += instance.distanceMatrix[0][customer_id] * distanceWeight;
        score += getRandomFractionFast() * noiseMagnitude;
        scoredCustomers.emplace_back(score, customer_id);
    }

    std::sort(scoredCustomers.rbegin(), scoredCustomers.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}