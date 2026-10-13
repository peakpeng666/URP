#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle
#include <vector>    // For std::vector
#include <limits>    // For std::numeric_limits
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast etc.

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentClusterCustomers; // Stores customers currently selected to expand from

    int numCustomersToRemove = getRandomNumber(10, 20); // Small number of customers

    // Select an initial random customer as the seed for the first "cluster"
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    currentClusterCustomers.push_back(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int nextCustomerToAdd = -1;

        // With high probability, try to select a customer close to an already selected one
        // This promotes selecting connected groups of customers
        if (getRandomFractionFast() < 0.85F && !currentClusterCustomers.empty()) { // 85% chance to pick close
            // Randomly pick one of the already selected customers to expand from
            int baseCustomer = currentClusterCustomers[getRandomNumber(0, currentClusterCustomers.size() - 1)];

            const auto& neighbors = sol.instance.adj[baseCustomer];
            // Iterate through a few closest neighbors to find an unselected one
            for (int i = 0; i < std::min((int)neighbors.size(), 10); ++i) { // Check up to 10 closest neighbors
                int neighbor = neighbors[i];
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    nextCustomerToAdd = neighbor;
                    break;
                }
            }
        }

        // Fallback: If no suitable neighbor was found (or if random chance failed), pick a completely random unselected customer
        if (nextCustomerToAdd == -1) {
            do {
                nextCustomerToAdd = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.find(nextCustomerToAdd) != selectedCustomersSet.end());
        }

        selectedCustomersSet.insert(nextCustomerToAdd);
        currentClusterCustomers.push_back(nextCustomerToAdd); // Add to the pool for future expansions
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Ordering of the removed customers for reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers based on a "reinsertion priority" score.
    // The strategy is to prioritize high-demand customers, then customers closer to the depot.
    // This helps ensure critical (high-demand) customers find a spot, and allows for efficient
    // routing from the depot for those nearby.
    // Stochasticity is added to ensure diversity over many iterations.

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerId : customers) {
        float demand = static_cast<float>(instance.demand[customerId]);
        float distToDepot = instance.distanceMatrix[0][customerId];

        // Combine demand and distance into a single score.
        // We want higher demand customers first, then lower distance.
        // Multiply demand by a large constant to give it higher priority than distance.
        float score = -demand * 1000.0F + distToDepot;

        // Add stochastic noise to the score to ensure diversity in sorting
        // The noise is small relative to the primary components of the score
        score += getRandomFractionFast() * 1.0F; // Add noise in range [0.0, 1.0]

        scoredCustomers.push_back({score, customerId});
    }

    // Sort the customers based on their calculated scores in ascending order
    // (since higher demand is negative, it will appear first)
    std::sort(scoredCustomers.begin(), scoredCustomers.end());

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}