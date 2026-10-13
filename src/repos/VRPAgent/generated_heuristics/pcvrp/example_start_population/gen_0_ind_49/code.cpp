#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <limits>
#include <vector>
#include <cmath>
#include <utility> // For std::pair

// Assuming getRandomNumber and getRandomFraction are globally available from Utils.h

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomers = sol.instance.numCustomers;
    // Determine the number of customers to remove, ensuring it's within a small, reasonable range
    // for LNS and doesn't exceed the total number of customers.
    int numCustomersToRemove = getRandomNumber(10, 30); 
    numCustomersToRemove = std::min(numCustomersToRemove, numCustomers);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesPool; // Customers whose neighbors are potential candidates for selection
    // `inCandidatesPool` tracks if a customer ID is currently present in `candidatesPool` for O(1) checks.
    std::vector<bool> inCandidatesPool(numCustomers + 1, false);

    // `minDistToSelected` stores the minimum distance from each customer to any already selected customer.
    // This helps in prioritizing customers closer to the growing cluster of removed customers.
    std::vector<float> minDistToSelected(numCustomers + 1, std::numeric_limits<float>::max());

    // 1. Initial Seed Customer: Pick a random customer to start the removal cluster.
    // This ensures stochasticity in the initial point of the removal.
    int seedCustomer = getRandomNumber(1, numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    minDistToSelected[seedCustomer] = 0.0f; // Distance from itself to the selected set is 0

    // Add immediate neighbors of the seed customer to the candidates pool.
    // These are the first potential candidates for expanding the removal cluster.
    for (int neighbor : sol.instance.adj[seedCustomer]) {
        // Ensure the neighbor is not already selected and not already in the candidates pool.
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            if (!inCandidatesPool[neighbor]) {
                candidatesPool.push_back(neighbor);
                inCandidatesPool[neighbor] = true;
                // Initialize its minimum distance to the selected set.
                minDistToSelected[neighbor] = sol.instance.distanceMatrix[seedCustomer][neighbor];
            }
        }
    }

    // 2. Iterative Expansion: Continuously add customers until the desired number to remove is reached.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // If `candidatesPool` becomes empty, it means all neighbors of the currently selected customers
        // have either been selected or added to the pool. To continue reaching `numCustomersToRemove`,
        // pick a new random unselected customer to start a disconnected removal cluster.
        if (candidatesPool.empty()) {
            int newSeed = -1;
            // Iterate a limited number of times to find an unselected customer, preventing infinite loops.
            const int maxAttempts = numCustomers * 2; 
            for (int attempts = 0; attempts < maxAttempts; ++attempts) {
                int potentialSeed = getRandomNumber(1, numCustomers);
                if (selectedCustomersSet.find(potentialSeed) == selectedCustomersSet.end()) {
                    newSeed = potentialSeed;
                    break;
                }
            }
            if (newSeed == -1) break; // If no new seed can be found, stop.

            selectedCustomersSet.insert(newSeed);
            minDistToSelected[newSeed] = 0.0f;

            // Add neighbors of this new seed to the candidates pool, similar to the initial seed.
            for (int neighbor : sol.instance.adj[newSeed]) {
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    if (!inCandidatesPool[neighbor]) {
                        candidatesPool.push_back(neighbor);
                        inCandidatesPool[neighbor] = true;
                        minDistToSelected[neighbor] = std::min(minDistToSelected[neighbor], sol.instance.distanceMatrix[newSeed][neighbor]);
                    }
                }
            }
            continue; // Continue to the next iteration of the while loop to pick from the updated candidates pool.
        }

        // Prepare candidates for stochastic selection based on their proximity.
        std::vector<std::pair<float, int>> scoredCandidates;
        for (int candidateId : candidatesPool) {
            // Ensure the candidate is still valid (not already selected and still in the pool).
            if (selectedCustomersSet.find(candidateId) == selectedCustomersSet.end() && inCandidatesPool[candidateId]) {
                 // Calculate a score: inversely proportional to its minimum distance to the selected cluster.
                 // A small epsilon (0.1f) is added to the distance to prevent division by zero for very close customers.
                float score = 1.0f / (minDistToSelected[candidateId] + 0.1f);
                // Add a small random noise to the score. This introduces diversity in selections
                // without entirely overriding the proximity-based preference.
                score += getRandomFraction(-0.01f, 0.01f) * score; 
                scoredCandidates.push_back({score, candidateId});
            }
        }

        // Fallback for an unlikely empty `scoredCandidates` (should be handled by `candidatesPool.empty()` check)
        if (scoredCandidates.empty()) {
            break; 
        }

        // Sort the candidates by their scores in descending order (highest score first).
        std::sort(scoredCandidates.rbegin(), scoredCandidates.rend());

        // Select a customer from the top N candidates to balance greedy choice (closer customers)
        // with stochasticity (random selection within the top tier).
        const int topNCandidates = std::min((int)scoredCandidates.size(), 50); // Consider up to top 50 candidates
        int chosenIdx = getRandomNumber(0, topNCandidates - 1);
        int chosenCustomer = scoredCandidates[chosenIdx].second;

        // Add the chosen customer to the set of selected customers.
        selectedCustomersSet.insert(chosenCustomer);
        minDistToSelected[chosenCustomer] = 0.0f; // Update its own minimum distance to 0

        // Remove the `chosenCustomer` from `candidatesPool` and mark it as no longer in the pool.
        // Rebuilding the vector is simple and robust, performance is acceptable for small removal counts.
        std::vector<int> nextCandidatesPool;
        for (int c : candidatesPool) {
            if (c != chosenCustomer) {
                nextCandidatesPool.push_back(c);
            } else {
                inCandidatesPool[c] = false; // Mark as removed from pool
            }
        }
        candidatesPool = nextCandidatesPool; // Update the candidatesPool

        // Update `minDistToSelected` for remaining candidates and add new neighbors of `chosenCustomer`
        // to `candidatesPool`.
        for (int neighbor : sol.instance.adj[chosenCustomer]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) { // If neighbor is not yet selected
                // Update minimum distance to selected cluster for this neighbor.
                minDistToSelected[neighbor] = std::min(minDistToSelected[neighbor], sol.instance.distanceMatrix[chosenCustomer][neighbor]);

                if (!inCandidatesPool[neighbor]) { // If neighbor is not already in the candidates pool, add it.
                    candidatesPool.push_back(neighbor);
                    inCandidatesPool[neighbor] = true;
                }
            }
        }
    }

    // Return the final list of selected customer IDs.
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function to order the removed customers for reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    
    // Sort customers based on static properties from the `Instance` to guide reinsertion.
    // The objective is to prioritize customers that are likely to be "easy" or "profitable" to reinsert.
    // A common metric for PCVRP is prize density: prize per unit cost.
    // Here, we use prize divided by distance to depot as a proxy for value density,
    // assuming closer customers are cheaper to serve and potentially form new profitable tours.

    for (int customerId : customers) {
        float currentPrize = instance.prizes[customerId];
        float distToDepot = instance.distanceMatrix[0][customerId];

        // Ensure non-zero distance to avoid division by zero.
        if (distToDepot < 0.1f) {
            distToDepot = 0.1f;
        }

        // Calculate a basic score representing "prize density".
        float score = currentPrize / distToDepot;

        // Add stochastic noise to the score. This is crucial for maintaining diversity
        // over millions of iterations, preventing the LNS from getting stuck in local optima
        // by always reinserting customers in the exact same deterministic order.
        // The noise is relative to the score magnitude to ensure meaningful perturbations.
        score += getRandomFraction(-0.1f, 0.1f) * score; 

        scoredCustomers.push_back({score, customerId});
    }

    // Sort the customers in descending order of their calculated scores.
    // Customers with higher scores (higher prize density) will be prioritized for reinsertion.
    std::sort(scoredCustomers.rbegin(), scoredCustomers.rend());

    // Populate the original `customers` vector with the newly sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}