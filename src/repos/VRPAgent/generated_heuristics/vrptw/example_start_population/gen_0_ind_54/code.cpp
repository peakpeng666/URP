#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <numeric>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatePool;

    int numCustomersToRemove = getRandomNumber(10, 20);

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialCustomer);
    candidatePool.push_back(initialCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            int safety_break_counter = 0;
            while (selectedCustomers.count(newSeed) && safety_break_counter < sol.instance.numCustomers) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                safety_break_counter++;
            }
            if (!selectedCustomers.count(newSeed)) {
                selectedCustomers.insert(newSeed);
                candidatePool.push_back(newSeed);
            }
            if (selectedCustomers.size() == numCustomersToRemove) break;
        }

        int currentIdx = getRandomNumber(0, candidatePool.size() - 1);
        int customerForExpansion = candidatePool[currentIdx];

        candidatePool[currentIdx] = candidatePool.back();
        candidatePool.pop_back();

        int numNeighborsToConsider = std::min((int)sol.instance.adj[customerForExpansion].size(), getRandomNumber(3, 7));

        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[customerForExpansion][i];
            if (neighbor == 0) continue;
            if (selectedCustomers.count(neighbor)) continue;

            if (getRandomFraction() < 0.7) {
                selectedCustomers.insert(neighbor);
                candidatePool.push_back(neighbor);
                if (selectedCustomers.size() == numCustomersToRemove) break;
            }
        }
    }
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerId : customers) {
        float score = instance.TW_Width[customerId];
        score += instance.startTW[customerId] * 0.1f;
        score += getRandomFraction() * 5.0f;

        scoredCustomers.push_back({score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}