#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::min, std::sort
#include <utility>   // For std::pair
#include "Utils.h"   // Assumed to provide getRandomNumber, getRandomFraction

// Customer selection heuristic for Large Neighborhood Search
// Aims to select a subset of customers that are somewhat clustered but
// also introduces stochasticity and allows for general exploration.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    const Instance& instance = sol.instance;

    // Tunable parameters for the selection process
    const int minCustomersToRemove = 20; // Minimum number of customers to remove
    const int maxCustomersToRemove = 50; // Maximum number of customers to remove
    const int proximityNeighborsToCheck = 10; // Number of closest neighbors to consider from adj list
    const float randomSelectionFallbackProb = 0.2f; // Probability to select a completely random customer

    // Determine the number of customers to remove for this iteration
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    // If no customers are to be removed, return an empty vector
    if (numCustomersToRemove <= 0) {
        return {};
    }

    // Start with an initial random seed customer
    // Customer IDs are 1-based, so generate from 1 to instance.numCustomers.
    int initialCustomer = getRandomNumber(1, instance.numCustomers);
    selectedCustomers.insert(initialCustomer);

    // Iteratively select more customers until the target number is reached
    while (selectedCustomers.size() < numCustomersToRemove) {
        // Decide whether to pick a completely random customer or a proximity-based one
        // A random selection is always performed if no customers have been selected yet
        if (getRandomFraction() < randomSelectionFallbackProb || selectedCustomers.empty()) {
            int randomCustomerCandidate;
            int safetyCounter = 0;
            // Loop to find an unselected random customer
            do {
                randomCustomerCandidate = getRandomNumber(1, instance.numCustomers);
                safetyCounter++;
                // Break if we've tried too many times (implies nearly all customers are selected)
                if (safetyCounter > instance.numCustomers * 2) {
                    break;
                }
            } while (selectedCustomers.count(randomCustomerCandidate)); // Check if already selected

            // If a new customer was successfully found, add it
            if (selectedCustomers.count(randomCustomerCandidate) == 0) {
                selectedCustomers.insert(randomCustomerCandidate);
            } else {
                // If we failed to find a new random customer (e.g., all customers selected),
                // it implies we've selected as many unique customers as possible.
                break;
            }
        } else {
            // Proximity-based selection: build a pool of candidates from neighbors of selected customers
            std::vector<int> candidatePool;
            for (int s : selectedCustomers) {
                // Ensure the customer ID 's' is a valid index for the adjacency list
                // (assuming adj is 0-indexed where index 0 is depot and 1 to N are customers)
                if (s >= 0 && s < instance.adj.size()) {
                    // Iterate through 's's closest neighbors (up to proximityNeighborsToCheck)
                    for (size_t i = 0; i < std::min((size_t)proximityNeighborsToCheck, instance.adj[s].size()); ++i) {
                        int neighbor = instance.adj[s][i];
                        // Ensure the neighbor is a valid customer ID (1 to instance.numCustomers)
                        // and not already in the selected set
                        if (neighbor >= 1 && neighbor <= instance.numCustomers &&
                            selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                            candidatePool.push_back(neighbor);
                        }
                    }
                }
            }

            // If there are candidates in the pool, select one randomly
            if (!candidatePool.empty()) {
                int chosenCandidate = candidatePool[getRandomNumber(0, candidatePool.size() - 1)];
                selectedCustomers.insert(chosenCandidate);
            } else {
                // Fallback to random selection if no suitable neighbors were found.
                // This can happen if all neighbors of selected customers are already selected.
                int randomCustomerCandidate;
                int safetyCounter = 0;
                do {
                    randomCustomerCandidate = getRandomNumber(1, instance.numCustomers);
                    safetyCounter++;
                    if (safetyCounter > instance.numCustomers * 2) {
                        break;
                    }
                } while (selectedCustomers.count(randomCustomerCandidate));

                if (selectedCustomers.count(randomCustomerCandidate) == 0) {
                    selectedCustomers.insert(randomCustomerCandidate);
                } else {
                    break;
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function to sort the removed customers for greedy reinsertion
// Prioritizes customers with higher prize and lower distance to the depot,
// adding a small stochastic element for diversity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Vector to store pairs of (calculated_score, customer_ID)
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    // Tunable parameters for score calculation
    // This weight determines how much distance to depot negatively impacts the score.
    const float distanceWeight = 0.1f;
    // This range adds random noise to scores to ensure different orders for similar scores.
    const float stochasticNoiseRange = 0.01f;

    for (int customerId : customers) {
        // Retrieve prize for the customer
        // Assuming instance.prizes is indexed by customer ID (1-based) or nodes (0-based)
        // If it's 0-indexed where index 0 is depot, then customerId directly corresponds to index.
        float prize = instance.prizes[customerId];
        // Retrieve distance from the depot (node 0) to the customer
        float distToDepot = instance.distanceMatrix[0][customerId];

        // Calculate a composite score: higher prize is better, lower distance is better
        // This score balances the value of the prize with the cost of reaching the customer from the depot.
        float score = prize - (distanceWeight * distToDepot);

        // Add a small random noise to the score for stochasticity
        // This helps break ties and ensures a diverse set of reinsertion orders over many iterations.
        score += getRandomFraction(-stochasticNoiseRange, stochasticNoiseRange);

        scoredCustomers.push_back({score, customerId});
    }

    // Sort the customers in descending order based on their calculated scores
    // Customers with higher scores (more prize-efficient) will be reinserted first.
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the original 'customers' vector with the newly sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}