#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle
#include <vector>
#include <numeric>   // For std::iota
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesToProcess;

    int numCustomersToRemove = getRandomNumber(15, 30); // Target range for number of customers to remove

    // Ensure we don't try to remove more customers than available
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1; // Always remove at least one if possible
    } else if (numCustomersToRemove == 0) {
        return {}; // No customers to remove
    }

    // 1. Select initial seed customer
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    candidatesToProcess.push_back(initialCustomer);

    // 2. Iteratively expand the set of selected customers
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesToProcess.empty()) {
            // All candidates exhausted, or unable to find new neighbors.
            // Pick a completely random unselected customer to continue growth.
            int newRandomCustomer = -1;
            int attempts = 0;
            const int maxAttempts = sol.instance.numCustomers * 2; // Prevent infinite loop for very small instances

            while (attempts < maxAttempts) {
                newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(newRandomCustomer) == selectedCustomersSet.end()) {
                    break;
                }
                attempts++;
            }

            if (newRandomCustomer != -1 && selectedCustomersSet.find(newRandomCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(newRandomCustomer);
                candidatesToProcess.push_back(newRandomCustomer);
            } else {
                // Should not happen if numCustomersToRemove < sol.instance.numCustomers
                // but as a fallback to prevent infinite loop
                break;
            }
        }

        // Randomly pick a customer from the already selected ones to expand from
        int pivotIdx = getRandomNumber(0, candidatesToProcess.size() - 1);
        int pivotCustomer = candidatesToProcess[pivotIdx];

        // Find a neighbor of the pivotCustomer to add
        const auto& neighbors = sol.instance.adj[pivotCustomer];
        
        int neighborToAdd = -1;
        int maxNeighborsToConsider = std::min((int)neighbors.size(), 10); // Consider first few closest neighbors
        
        // Try a few times to find an unselected neighbor from the closest ones
        for (int i = 0; i < 5; ++i) { // Limit attempts to find a neighbor
            if (maxNeighborsToConsider == 0) break;
            int neighborSearchIdx = getRandomNumber(0, maxNeighborsToConsider - 1);
            int candidateNeighbor = neighbors[neighborSearchIdx];

            if (candidateNeighbor != 0 && selectedCustomersSet.find(candidateNeighbor) == selectedCustomersSet.end()) {
                neighborToAdd = candidateNeighbor;
                break;
            }
        }

        if (neighborToAdd != -1) {
            selectedCustomersSet.insert(neighborToAdd);
            candidatesToProcess.push_back(neighborToAdd);
        } else {
            // If no valid neighbor was found for the pivot customer after attempts,
            // remove it from candidatesToProcess (if it's not the only one) to avoid getting stuck on it.
            // For simplicity and speed, just leave it in; subsequent random picks will likely find other candidates.
            // Or we could remove it: candidatesToProcess.erase(candidatesToProcess.begin() + pivotIdx);
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers based on a "difficulty" score for reinsertion.
    // Higher demand and greater distance from depot usually make reinsertion harder.
    // Add stochasticity using a random component.

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        // Score based on demand and distance from depot (node 0)
        float score = static_cast<float>(instance.demand[customerId]);
        score += instance.distanceMatrix[0][customerId] * 0.1f; // Weight distance less than demand

        // Add a small random component for stochasticity
        // Scale random component relative to vehicle capacity to ensure it's meaningful
        score += getRandomFractionFast() * (instance.vehicleCapacity * 0.005f);

        customerScores.push_back({score, customerId});
    }

    // Sort in descending order of score (harder customers first)
    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}