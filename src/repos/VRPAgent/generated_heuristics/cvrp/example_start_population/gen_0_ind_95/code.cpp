#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>
#include "Utils.h"

int getRandomCustomerId(int numCustomers) {
    return getRandomNumber(1, numCustomers);
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesToExpandFrom;

    int numCustomersToRemove = getRandomNumber(
        std::max(10, (int)(sol.instance.numCustomers * 0.02)),
        std::min(30, (int)(sol.instance.numCustomers * 0.05))
    );

    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int initialSeed = getRandomCustomerId(sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeed);
    candidatesToExpandFrom.push_back(initialSeed);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesToExpandFrom.empty()) {
            int newSeed = getRandomCustomerId(sol.instance.numCustomers);
            while (selectedCustomersSet.count(newSeed)) {
                newSeed = getRandomCustomerId(sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newSeed);
            candidatesToExpandFrom.push_back(newSeed);
            if (selectedCustomersSet.size() == numCustomersToRemove) {
                break;
            }
        }

        int randIdx = getRandomNumber(0, candidatesToExpandFrom.size() - 1);
        int currentCustomer = candidatesToExpandFrom[randIdx];

        bool added_any_neighbor = false;
        for (int neighbor : sol.instance.adj[currentCustomer]) {
            if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && !selectedCustomersSet.count(neighbor)) {
                if (getRandomFractionFast() < 0.6f) {
                    selectedCustomersSet.insert(neighbor);
                    candidatesToExpandFrom.push_back(neighbor);
                    added_any_neighbor = true;
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        goto end_selection;
                    }
                }
            }
        }
        if (!added_any_neighbor && candidatesToExpandFrom.size() > 1) {
            candidatesToExpandFrom.erase(candidatesToExpandFrom.begin() + randIdx);
        } else if (candidatesToExpandFrom.size() == 1 && !added_any_neighbor) {
            candidatesToExpandFrom.clear();
        }
    }

end_selection:;
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    float noiseMagnitude = 100.0f; 

    for (int customerId : customers) {
        float score = instance.distanceMatrix[0][customerId] + (float)instance.demand[customerId];
        score += getRandomFractionFast() * noiseMagnitude;
        scoredCustomers.push_back({score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}