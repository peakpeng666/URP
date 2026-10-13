#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

// Customer selection heuristic for the Large Neighborhood Search (LNS) framework.
// This function identifies a subset of customers to be removed from the current solution.
// The selection strategy prioritizes picking customers that are geographically close to
// already selected customers, while also incorporating stochastic elements for diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove. This is a small percentage of total customers.
    // For 500 customers, this range typically falls between 20 and 33 customers (4% to 6.6%).
    int numCustomersToRemove = getRandomNumber(sol.instance.numCustomers / 25, sol.instance.numCustomers / 15);
    if (numCustomersToRemove < 1) { // Ensure at least one customer is selected for removal.
        numCustomersToRemove = 1;
    }

    std::vector<int> selectedCustomers;
    selectedCustomers.reserve(numCustomersToRemove); // Pre-allocate memory for efficiency.
    // A boolean array to quickly check if a customer has already been selected.
    std::vector<bool> isCustomerSelected(sol.instance.numCustomers + 1, false);

    // This vector acts as a dynamic pool of "attractive" candidates for selection.
    // It primarily stores neighbors of already selected customers, ensuring that
    // subsequent selections tend to be spatially coherent.
    std::vector<int> attractionPool;
    // Heuristic reserve for the attraction pool to minimize reallocations.
    attractionPool.reserve(numCustomersToRemove * 10);

    // Probability to favor selecting a customer from the 'attractionPool'.
    // A higher value encourages more clustered removals, supporting the
    // requirement that selected customers should be close to others.
    const float neighborSelectionProbability = 0.8f;

    // Step 1: Select the very first customer randomly. This serves as the initial seed
    // for the connected component of removed customers.
    int firstCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.push_back(firstCustomer);
    isCustomerSelected[firstCustomer] = true;

    // Add all unselected neighbors of the `firstCustomer` to the `attractionPool`.
    // The `adj` list provides neighbors sorted by distance, which is useful here.
    for (int neighborId : sol.instance.adj[firstCustomer]) {
        // Ensure the neighbor is a customer (ID > 0) and not yet selected.
        if (neighborId > 0 && !isCustomerSelected[neighborId]) {
            attractionPool.push_back(neighborId);
        }
    }

    // Step 2: Iteratively select the remaining customers until the target `numCustomersToRemove` is met.
    while (selectedCustomers.size() < numCustomersToRemove) {
        int nextCustomerCandidate = -1; // Initialize with an invalid customer ID.

        // With `neighborSelectionProbability`, attempt to pick from the `attractionPool`.
        if (!attractionPool.empty() && getRandomFractionFast() < neighborSelectionProbability) {
            // Loop a limited number of times to find a valid (unselected) customer from the pool.
            // This handles cases where a customer picked from the pool might have already been selected
            // (e.g., through a different path or previous selection).
            const int maxPoolAttempts = 50; 
            for (int attempt = 0; attempt < maxPoolAttempts; ++attempt) {
                // Randomly pick an index from the current `attractionPool`.
                int poolIdx = getRandomNumber(0, attractionPool.size() - 1);
                nextCustomerCandidate = attractionPool[poolIdx];
                
                // Immediately remove the chosen customer from the pool. This prevents it from being
                // picked again in subsequent attempts within this same selection iteration.
                // Using swap and pop_back is efficient for vector removal.
                std::swap(attractionPool[poolIdx], attractionPool.back());
                attractionPool.pop_back();

                // If the candidate customer is not yet selected, it's a valid choice; break the loop.
                if (!isCustomerSelected[nextCustomerCandidate]) {
                    break;
                }
                nextCustomerCandidate = -1; // Reset if invalid, to force another attempt.
            }
        }

        // If no valid customer was found from the `attractionPool` (e.g., pool empty, probability
        // didn't favor it, or all pool attempts failed), fall back to picking a completely random,
        // unselected customer from the entire set of customers.
        if (nextCustomerCandidate == -1) {
            const int maxRandomAttempts = 100; // Limit attempts to find a random unselected customer.
            for (int attempt = 0; attempt < maxRandomAttempts; ++attempt) {
                nextCustomerCandidate = getRandomNumber(1, sol.instance.numCustomers);
                if (!isCustomerSelected[nextCustomerCandidate]) {
                    break; // Found an unselected random customer.
                }
                nextCustomerCandidate = -1; // Reset if already selected, try again.
            }

            // As a robust fallback (highly unlikely to be triggered given small `numCustomersToRemove`),
            // if even random attempts fail, iterate through all customers sequentially to find the first unselected one.
            if (nextCustomerCandidate == -1) {
                bool found = false;
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (!isCustomerSelected[i]) {
                        nextCustomerCandidate = i;
                        found = true;
                        break;
                    }
                }
                if (!found) { // No more customers to select; this should only happen if all customers are selected.
                    break;
                }
            }
        }

        // Add the determined `nextCustomerCandidate` to the list of `selectedCustomers`.
        selectedCustomers.push_back(nextCustomerCandidate);
        isCustomerSelected[nextCustomerCandidate] = true;

        // Populate the `attractionPool` with unselected neighbors of the newly selected customer.
        for (int neighborId : sol.instance.adj[nextCustomerCandidate]) {
            if (neighborId > 0 && !isCustomerSelected[neighborId]) {
                attractionPool.push_back(neighborId);
            }
        }
    }

    return selectedCustomers;
}

// Function to sort the removed customers before their greedy reinsertion.
// The sorting strategy aims to prioritize "harder" customers (e.g., high demand, far from depot)
// to be reinserted first, as their placement might significantly influence the overall solution structure.
// Stochasticity is introduced to ensure diversity in the reinsertion order over many LNS iterations.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // A vector of pairs to store {score, customer_id} for sorting.
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size()); // Pre-allocate memory.

    // Define influence factors for various criteria contributing to the reinsertion score.
    // These weights are chosen to reflect the desired prioritization.
    // `demandInfluence` is high to make demand a primary sorting factor.
    const float demandInfluence = 1000.0f;
    // `distanceInfluence` affects customers further from the depot.
    const float distanceInfluence = 1.0f;
    // `randomNoiseMagnitude` adds a small, uniform random value to scores,
    // ensuring diverse sorting orders for customers with otherwise identical or very similar scores.
    const float randomNoiseMagnitude = 0.001f;

    for (int customerId : customers) {
        float score = 0.0f;
        // Customers with higher demand are generally harder to fit into routes due to capacity constraints.
        // Assign a higher score to prioritize them for earlier reinsertion.
        score += static_cast<float>(instance.demand[customerId]) * demandInfluence;
        
        // Customers located farther from the depot might require longer routes or more complex tour structures.
        // Assign a higher score to them to consider their placement earlier.
        score += instance.distanceMatrix[0][customerId] * distanceInfluence;

        // Add a small random component to the score. This is crucial for introducing stochasticity.
        // It helps break ties and ensures that the reinsertion order is not purely deterministic
        // across different LNS iterations, even with identical input customers.
        score += getRandomFractionFast() * randomNoiseMagnitude;

        scoredCustomers.push_back({score, customerId});
    }

    // Sort the `scoredCustomers` in descending order of their calculated scores.
    // This places customers deemed "harder" (higher demand, farther from depot) at the beginning
    // of the list, so they are reinserted first by the greedy reinsertion mechanism.
    std::sort(scoredCustomers.rbegin(), scoredCustomers.rend());

    // Update the original `customers` vector with the new, sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}