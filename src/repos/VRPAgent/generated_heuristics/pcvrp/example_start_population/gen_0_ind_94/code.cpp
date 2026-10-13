#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> potentialExpansionCustomers;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);
    potentialExpansionCustomers.push_back(seedCustomer);
    
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (potentialExpansionCustomers.empty()) {
            int newSeedCustomer = -1;
            int attempts = 0;
            const int maxAttempts = sol.instance.numCustomers * 2;

            while (attempts < maxAttempts) {
                newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(newSeedCustomer) == selectedCustomers.end()) {
                    break;
                }
                attempts++;
            }

            if (newSeedCustomer != -1 && selectedCustomers.find(newSeedCustomer) == selectedCustomers.end()) {
                selectedCustomers.insert(newSeedCustomer);
                potentialExpansionCustomers.push_back(newSeedCustomer);
            } else {
                break;
            }
        }

        int sourceIdx = getRandomNumber(0, potentialExpansionCustomers.size() - 1);
        int currentSourceCustomer = potentialExpansionCustomers[sourceIdx];
        
        potentialExpansionCustomers.erase(potentialExpansionCustomers.begin() + sourceIdx);

        const std::vector<int>& neighbors = sol.instance.adj[currentSourceCustomer];
        std::vector<int> availableNeighbors;

        int numNeighborsToCheck = std::min((int)neighbors.size(), getRandomNumber(3, 10)); 

        for (int i = 0; i < numNeighborsToCheck; ++i) {
            int neighborId = neighbors[i];
            if (neighborId > 0 && selectedCustomers.find(neighborId) == selectedCustomers.end()) {
                availableNeighbors.push_back(neighborId);
            }
        }

        if (!availableNeighbors.empty()) {
            int chosenNeighbor = availableNeighbors[getRandomNumber(0, availableNeighbors.size() - 1)];
            selectedCustomers.insert(chosenNeighbor);
            potentialExpansionCustomers.push_back(chosenNeighbor);
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
        float score = instance.prizes[customerId] * (1.0f + getRandomFractionFast() * 0.2f);
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}