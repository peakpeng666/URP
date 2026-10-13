#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;

    // Determine the number of customers to remove
    // A range like 10-25 is a good balance for large instances, providing enough perturbation
    // without making the reinsertion phase too complex or slow.
    int numCustomersToRemove = getRandomNumber(10, 25); 

    // Step 1: Select an initial random customer as a seed
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);

    // Step 2: Iteratively add customers that are spatially close to already selected customers
    // This promotes the removal of "clusters" or "connected regions" which can lead to meaningful local optimizations.
    while (selectedCustomers.size() < numCustomersToRemove) {
        int candidate = -1;
        
        // Try to find a spatially close customer from existing selected customers
        // We attempt a few retries to ensure we find a suitable neighbor or fallback.
        int maxRetries = 100; 
        for (int retry = 0; retry < maxRetries; ++retry) {
            // Choose a random customer from the set of already selected customers
            // This provides a stochastic anchor for finding the next customer.
            auto it = selectedCustomers.begin();
            std::advance(it, getRandomNumber(0, selectedCustomers.size() - 1));
            int pivotCustomer = *it;

            // Get neighbors of the pivot customer. The adj list is sorted by distance.
            const auto& neighbors = sol.instance.adj[pivotCustomer];

            // Consider only a limited number of the closest neighbors for efficiency and focus.
            // This balances exploring close neighbors with introducing some randomness.
            int numNeighborsToConsider = std::min((int)neighbors.size(), 50); 
            if (numNeighborsToConsider == 0) continue; // No neighbors for this pivot

            // Pick a random neighbor from the considered range
            int neighborIdx = getRandomNumber(0, numNeighborsToConsider - 1);
            int potentialCandidate = neighbors[neighborIdx];

            // Ensure the candidate is a valid customer (not depot) and not already selected
            if (potentialCandidate != 0 && selectedCustomers.find(potentialCandidate) == selectedCustomers.end()) {
                candidate = potentialCandidate;
                break; // Found a valid candidate, exit retry loop
            }
        }

        // If no suitable neighbor was found after retries (e.g., all neighbors are already selected
        // or depot), fall back to selecting a completely random unselected customer.
        // This ensures the loop always progresses and adds diversity if the localized search gets stuck.
        if (candidate == -1) {
            int randomUnselectedCustomer;
            do {
                randomUnselectedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomers.find(randomUnselectedCustomer) != selectedCustomers.end());
            selectedCustomers.insert(randomUnselectedCustomer);
        } else {
            selectedCustomers.insert(candidate);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Create pairs of (score, customer_id) for sorting.
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerId : customers) {
        // Calculate a "difficulty" or "impact" score for each customer.
        // Customers with higher demand are generally harder to place due to capacity constraints.
        // Customers further from the depot (node 0) are also generally harder to place as they extend tours more.
        float score = (float)instance.demand[customerId] + instance.distanceMatrix[0][customerId];

        // Introduce stochasticity by adding a small random perturbation to the score.
        // This ensures diversity in sorting order over many iterations, preventing stagnation.
        // The perturbation is a small fraction of the score to maintain general relative order.
        score += getRandomFractionFast() * 0.01f * score; 

        scoredCustomers.emplace_back(score, customerId);
    }

    // Sort customers in descending order of their score.
    // This means "harder" or "more impactful" customers are reinserted first.
    // The rationale is that by placing these challenging customers early, the greedy reinsertion
    // has more options and can potentially build a more robust tour structure around them,
    // leaving easier-to-place customers for later, when the tour structure is more defined.
    std::sort(scoredCustomers.rbegin(), scoredCustomers.rend());

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}