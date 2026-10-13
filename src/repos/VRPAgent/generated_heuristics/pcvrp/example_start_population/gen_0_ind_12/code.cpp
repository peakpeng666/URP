#include "AgentDesigned.h"
#include <vector>
#include <unordered_set>
#include <algorithm> // For std::sort, std::min
#include <cmath>     // For std::max
#include <random>    // Included in the original skeleton, though not directly used for random generation
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> selectionQueue;

    int numCustomersToRemove = getRandomNumber(15, 35);

    int initialSeed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeed);
    selectionQueue.push_back(initialSeed);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (selectionQueue.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomers.find(newSeed) == selectedCustomers.end()) {
                selectedCustomers.insert(newSeed);
                selectionQueue.push_back(newSeed);
            }
            if (selectedCustomers.size() >= numCustomersToRemove) break;
            continue;
        }

        int currentIdxInQueue = getRandomNumber(0, selectionQueue.size() - 1);
        int baseCustomer = selectionQueue[currentIdxInQueue];
        
        selectionQueue.erase(selectionQueue.begin() + currentIdxInQueue);

        const auto& neighbors = sol.instance.adj[baseCustomer];

        std::vector<int> potentialAdditions;
        int neighborsToCheck = std::min((int)neighbors.size(), 100); 

        for (int i = 0; i < neighborsToCheck; ++i) {
            int neighborId = neighbors[i];
            if (selectedCustomers.find(neighborId) == selectedCustomers.end()) {
                potentialAdditions.push_back(neighborId);
            }
        }

        if (!potentialAdditions.empty()) {
            int chosenCustomer = potentialAdditions[getRandomNumber(0, potentialAdditions.size() - 1)];
            selectedCustomers.insert(chosenCustomer);
            selectionQueue.push_back(chosenCustomer);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float prize = instance.prizes[customerId];
        float demand = instance.demand[customerId];

        float score = prize / std::max(1.0f, demand);

        score += (getRandomFraction() - 0.5f) * (prize * 0.2f);
        
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.rbegin(), customerScores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}