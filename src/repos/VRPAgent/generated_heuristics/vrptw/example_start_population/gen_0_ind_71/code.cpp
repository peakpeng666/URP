#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // Aim to remove between 15 and 35 customers.
    // For large instances (e.g., 500 customers), this range (3% to 7%) constitutes a "small number"
    // of customers to remove in each LNS iteration, as required.
    int numCustomersToRemoveTarget = getRandomNumber(15, 35);
    
    // Limits the number of closest neighbors to consider for expansion from a seed customer.
    // This ensures that the neighborhood expansion remains fast and focused, preventing
    // the selection of customers too far from the initial cluster.
    int maxNeighborsToConsider = 5; 
    
    // Probability for a considered neighbor to be added to the removal set.
    // Higher values lead to more compact and connected clusters of removed customers,
    // which aligns with the requirement that "each selected customer should be close
    // to at least one or a few other selected customers".
    float probAddNeighbor = 0.6f; // Using 'f' for float literal

    // Handle edge case where there are no customers to select from.
    if (sol.instance.numCustomers == 0) {
        return {}; 
    }

    // Safeguard to prevent infinite loops in selection, especially if `numCustomersToRemoveTarget`
    // is high relative to `sol.instance.numCustomers` or if all relevant customers are already picked.
    // The number of attempts is proportional to the target number of customers to remove.
    int attempts = 0;
    int maxAttempts = numCustomersToRemoveTarget * 10; 

    while (selectedCustomers.size() < numCustomersToRemoveTarget && attempts < maxAttempts) {
        attempts++;
        
        // Pick a random customer as a seed for initiating a removal cluster.
        // Customer IDs are 1-indexed (from 1 to sol.instance.numCustomers).
        int seedCustomer = getRandomNumber(1, sol.instance.numCustomers); 

        // Attempt to insert the seed customer into the set. `insert` returns a pair
        // where `.second` is true if the insertion took place (i.e., customer was new).
        if (selectedCustomers.insert(seedCustomer).second) { 
            // If the seed was successfully added, attempt to expand its neighborhood.
            // Check if the adjacency list exists for this `seedCustomer` ID (which corresponds to its node ID).
            if (seedCustomer < sol.instance.adj.size()) { 
                int neighborsAdded = 0;
                // Iterate through the closest neighbors of the seed customer using the precomputed adjacency list.
                for (int neighbor : sol.instance.adj[seedCustomer]) {
                    // Stop if we've considered enough neighbors or reached the overall target size.
                    if (neighborsAdded >= maxNeighborsToConsider || selectedCustomers.size() >= numCustomersToRemoveTarget) {
                        break; 
                    }

                    // Check if the neighbor is a valid customer ID (1 to sol.instance.numCustomers),
                    // if it hasn't been selected already, and if it passes the probabilistic check.
                    if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && 
                        selectedCustomers.count(neighbor) == 0 && getRandomFraction() < probAddNeighbor) {
                        
                        selectedCustomers.insert(neighbor); // Add the neighbor to the set.
                        neighborsAdded++; // Increment count of neighbors added from this seed.
                    }
                }
            }
        }
    }

    // Convert the `unordered_set` of selected customer IDs to a `std::vector` and return it.
    // This conversion is done at the very end to maximize efficiency during selection using the set's fast lookups.
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // This heuristic aims to order the removed customers for reinsertion such that
    // "harder" customers are attempted first. This can often lead to better overall
    // reinsertion outcomes as the greedy reinsertion has more flexibility for these
    // difficult customers initially.
    // Customers with tighter time windows (smaller TW_Width) are generally harder to place.
    // The primary sorting criterion is `TW_Width`, sorted in ascending order (tightest first).

    std::vector<std::pair<float, int>> sortKeys;
    sortKeys.reserve(customers.size()); // Reserve memory to prevent reallocations.

    for (int customerId : customers) {
        // Ensure the customerId is valid for accessing instance data (e.g., TW_Width).
        // Customer IDs are 1-indexed, corresponding to indices 1 to `numCustomers` in instance vectors.
        if (customerId >= 1 && customerId <= instance.numCustomers) {
            float twWidth = instance.TW_Width[customerId];
            
            // Introduce stochasticity by adding a small, relative random perturbation to the time window width.
            // This ensures that customers with identical or very similar TW_Widths are slightly shuffled,
            // preventing the LNS from getting stuck in local optima due to deterministic ordering.
            // The perturbation is +/- 5% of the customer's own time window width.
            float perturbation = twWidth * getRandomFraction(-0.05f, 0.05f); 
            
            sortKeys.push_back({twWidth + perturbation, customerId});
        }
        // No explicit handling for invalid customerId here, assuming the 'customers' vector
        // contains only valid IDs as generated by `select_by_llm_1`.
    }

    // Sort the `sortKeys` vector. The `std::pair` will be sorted based on its first element (the float key).
    // For the small number of customers (15-35), `std::sort` (an N log N algorithm) is very fast.
    std::sort(sortKeys.begin(), sortKeys.end());

    // Update the original `customers` vector with the new, sorted order derived from `sortKeys`.
    for (size_t i = 0; i < sortKeys.size(); ++i) {
        customers[i] = sortKeys[i].second;
    }
}