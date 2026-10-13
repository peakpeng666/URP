#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatesToExplore;

    int numCustomersToRemove = getRandomNumber(15, 30); 

    int firstCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(firstCustomer);
    candidatesToExplore.push_back(firstCustomer);

    int currentSeedIdx = 0;
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (currentSeedIdx >= candidatesToExplore.size()) {
            int newRandomCustomer;
            do {
                newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomers.count(newRandomCustomer));
            selectedCustomers.insert(newRandomCustomer);
            candidatesToExplore.push_back(newRandomCustomer);
            currentSeedIdx = candidatesToExplore.size() - 1; 
            if (selectedCustomers.size() == numCustomersToRemove) break;
        }

        int currentSeed = candidatesToExplore[currentSeedIdx];
        bool addedNewCustomer = false;

        for (int neighborNodeIdx : sol.instance.adj[currentSeed]) {
            if (neighborNodeIdx == 0) continue; 
            if (selectedCustomers.count(neighborNodeIdx) == 0) {
                if (getRandomFractionFast() < 0.8) { 
                    selectedCustomers.insert(neighborNodeIdx);
                    candidatesToExplore.push_back(neighborNodeIdx);
                    addedNewCustomer = true;
                    break;
                }
            }
        }

        if (!addedNewCustomer) {
            currentSeedIdx++;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float prizeC = instance.prizes[customerId];
        float demandC = instance.demand[customerId];

        float closestDist = -1.0f;
        for (int neighborNodeIdx : instance.adj[customerId]) {
            if (neighborNodeIdx == 0) continue; 
            closestDist = instance.distanceMatrix[customerId][neighborNodeIdx];
            break; 
        }

        if (closestDist == -1.0f) { 
            closestDist = 1000000.0f; 
        }

        // Score = (Prize * W_PRIZE) - (Demand * W_DEMAND) - (Closest Distance * W_DIST) + (Random component)
        // Higher score is better for reinsertion.
        // Encourage high prize, low demand, low closest distance.
        float score = prizeC - (demandC * 0.5f) - (closestDist * 0.1f) + (getRandomFractionFast() * 10.0f);
        
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort in descending order of score
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}