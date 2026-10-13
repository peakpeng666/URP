#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <utility>
#include "Utils.h"

// Customer selection heuristic for LNS step 1.
// Selects a subset of customers to remove, encouraging spatial proximity while ensuring diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesForExpansion; // Pool of selected customers from which to expand

    // Determine the number of customers to remove.
    // This range (e.g., 10-20) can be adjusted but should be a small fraction of total customers.
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    // Step 1: Select an initial seed customer randomly.
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    candidatesForExpansion.push_back(seedCustomer);

    // Step 2: Iteratively expand the set of selected customers until the target count is reached.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool addedNewCustomerInThisIteration = false;

        // If the current pool of candidates for expansion is exhausted (all their close neighbors are selected or failed probability checks),
        // pick a new random unselected customer to start a new cluster.
        if (candidatesForExpansion.empty()) {
            int newSeedAttempts = 0;
            // Limit attempts to find a new seed to prevent infinite loops in degenerate cases (e.g., very few customers).
            const int maxNewSeedAttempts = sol.instance.numCustomers * 2; 
            while (!addedNewCustomerInThisIteration && newSeedAttempts < maxNewSeedAttempts) {
                int potentialNewSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potentialNewSeed) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(potentialNewSeed);
                    candidatesForExpansion.push_back(potentialNewSeed);
                    addedNewCustomerInThisIteration = true;
                }
                newSeedAttempts++;
            }
            if (!addedNewCustomerInThisIteration) {
                // If unable to find a new seed after many attempts (should be rare for large instances),
                // break to return current set.
                break;
            }
        }
        
        // Randomly select an "anchor" customer from the existing selected customers (candidatesForExpansion)
        // to try and expand from its vicinity.
        int anchorIdx = getRandomNumber(0, candidatesForExpansion.size() - 1);
        int anchorCustomer = candidatesForExpansion[anchorIdx];

        bool foundNeighborToAdd = false;
        // Iterate through neighbors of the anchor customer, ordered by distance (instance.adj provides this).
        for (int neighborId : sol.instance.adj[anchorCustomer]) {
            // Ensure the neighbor is a customer (not the depot, which is node 0) and not already selected.
            if (neighborId != 0 && selectedCustomersSet.find(neighborId) == selectedCustomersSet.end()) {
                // Introduce stochasticity: a probability of selecting this neighbor.
                // This adds diversity to the clusters generated over many LNS iterations.
                float selectionProb = 0.8f; // Example: 80% chance to select the first eligible neighbor.
                
                // If we're one customer away from the target count, force addition to ensure we reach numCustomersToRemove.
                if (getRandomFractionFast() < selectionProb || selectedCustomersSet.size() == numCustomersToRemove - 1) {
                    selectedCustomersSet.insert(neighborId);
                    candidatesForExpansion.push_back(neighborId); // The newly added customer can also serve as an expansion point.
                    foundNeighborToAdd = true;
                    addedNewCustomerInThisIteration = true;
                    break; // Move to the next iteration of the outer while loop (found a customer).
                }
            }
        }
        
        // If no new neighbor was added from this anchor customer (either all were selected, or failed probability check),
        // remove it from the `candidatesForExpansion` pool. This prevents repeatedly trying to expand from an exhausted point
        // and encourages exploration of other parts of the growing cluster or starting new clusters.
        if (!foundNeighborToAdd) {
            std::swap(candidatesForExpansion[anchorIdx], candidatesForExpansion.back());
            candidatesForExpansion.pop_back();
        }
    }

    // Convert the unordered_set to a vector for return.
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Customer ordering heuristic for LNS step 3.
// Sorts the removed customers for reinsertion, prioritizing by demand with added stochasticity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    // Calculate a score for each customer.
    // Higher demand customers are often more challenging to place due to vehicle capacity constraints.
    // Prioritizing them during reinsertion can sometimes lead to better overall solutions by ensuring they are accommodated.
    for (int customerId : customers) {
        float score = static_cast<float>(instance.demand[customerId]);
        
        // Add a small random perturbation to the score.
        // This introduces stochasticity, breaking ties among customers with similar demands
        // and ensuring diverse reinsertion orders across multiple LNS iterations.
        // The perturbation range (e.g., 0 to 0.1) is kept small to ensure demand remains the primary sorting factor.
        score += getRandomFractionFast() * 0.1f; 
        
        customerScores.push_back({score, customerId});
    }

    // Sort customers in descending order of their calculated score.
    // Customers with higher scores (e.g., higher demand + noise) will be considered for reinsertion first.
    std::sort(customerScores.begin(), customerScores.end(), std::greater<std::pair<float, int>>());

    // Update the original `customers` vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}