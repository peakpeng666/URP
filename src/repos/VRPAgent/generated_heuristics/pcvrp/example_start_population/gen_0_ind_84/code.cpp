#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::min, std::sort, std::shuffle
#include <utility>   // For std::pair, std::swap

// Assuming Solution, Instance, Tour, and Utils.h functions are available via headers.
// Specifically, getRandomNumber, getRandomFractionFast.

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove. A range of 20-50 for 500+ customers is
    // chosen to be a "small number" as required, while allowing significant changes.
    int numCustomersToRemove = getRandomNumber(20, 50);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesForExpansion; // Customers whose neighbors we consider for selection

    // Loop until the desired number of customers are selected
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // If the expansion candidates are exhausted, pick a new random seed customer
        if (candidatesForExpansion.empty()) {
            int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            // Ensure the seed is not already selected to avoid infinite loops if numToRemove is large
            while (selectedCustomersSet.count(seedCustomer) > 0) {
                seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(seedCustomer);
            candidatesForExpansion.push_back(seedCustomer);
            if (selectedCustomersSet.size() == numCustomersToRemove) break; // Break if target reached
        }

        // Randomly pick a customer from the current candidates to expand from
        int randomIdx = getRandomNumber(0, candidatesForExpansion.size() - 1);
        int currentCustomer = candidatesForExpansion[randomIdx];
        
        // Use swap-and-pop for O(1) average time removal from vector
        // This makes the removal faster than vector.erase() which is O(N)
        if (randomIdx != candidatesForExpansion.size() - 1) {
            std::swap(candidatesForExpansion[randomIdx], candidatesForExpansion.back());
        }
        candidatesForExpansion.pop_back();

        // Limit the number of closest neighbors to check for expansion
        // This keeps the selection process fast for large instances.
        int maxNeighborsToCheck = 5; 
        
        // Iterate through the closest neighbors of the current customer
        for (int j = 0; j < std::min(maxNeighborsToCheck, (int)sol.instance.adj[currentCustomer].size()); ++j) {
            int neighbor = sol.instance.adj[currentCustomer][j];
            
            // Skip depot (node 0) or invalid customer IDs
            if (neighbor == 0 || neighbor > sol.instance.numCustomers) continue;

            // If the neighbor is not already selected
            if (selectedCustomersSet.count(neighbor) == 0) {
                // Probabilistic selection: closer neighbors (smaller j) have higher probability
                // Example: j=0 -> 1.0 prob, j=1 -> 0.85 prob, j=2 -> 0.7 prob, etc.
                float selectionProb = 1.0f - (j * 0.15f); 
                
                if (getRandomFractionFast() < selectionProb) {
                    selectedCustomersSet.insert(neighbor);
                    candidatesForExpansion.push_back(neighbor); // Add to candidates for future expansion
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        // Use a goto to break out of nested loops efficiently
                        goto endSelectionLoop; 
                    }
                }
            }
        }
    }
endSelectionLoop:; // Label for the goto statement

    // Convert the set of selected customers to a vector for return
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // This function sorts the customers based on a dynamically weighted scoring system
    // incorporating various static properties of the customers.
    // This introduces stochasticity and allows different sorting priorities in each LNS iteration.

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    // Generate random weights for each scoring component.
    // These weights will influence the "focus" of the sorting for this specific iteration.
    // Multipliers (e.g., *2.0f, *1.5f) are chosen to give higher potential weight to certain factors.
    float wPrize = getRandomFractionFast() * 2.0f;     // Weight for customer prize (higher preferred)
    float wDist = getRandomFractionFast() * 1.5f;      // Weight for inverse distance to depot (closer preferred)
    float wDemand = getRandomFractionFast() * 1.0f;    // Weight for inverse demand (lower preferred, easier to fit)
    float wAdj = getRandomFractionFast() * 0.5f;       // Weight for adjacency list size (more connections preferred)

    // Normalize weights to sum to 1 to ensure consistent scaling
    float sumWeights = wPrize + wDist + wDemand + wAdj;
    if (sumWeights == 0) sumWeights = 1.0f; // Avoid division by zero if all weights are zero (unlikely but safe)
    wPrize /= sumWeights;
    wDist /= sumWeights;
    wDemand /= sumWeights;
    wAdj /= sumWeights;

    // Calculate a score for each customer based on weighted properties
    for (int customerId : customers) {
        float score = 0.0f;

        // Component 1: Prize - Directly proportional, higher prize is better
        score += wPrize * instance.prizes[customerId];

        // Component 2: Distance to depot - Inversely proportional, closer is better.
        // Add 1.0f to the denominator to prevent division by zero and to scale.
        score += wDist * (1.0f / (1.0f + instance.distanceMatrix[0][customerId]));

        // Component 3: Demand - Inversely proportional, lower demand is better (easier to fit into tours)
        score += wDemand * (1.0f / (1.0f + instance.demand[customerId]));

        // Component 4: Connectivity - Directly proportional to number of neighbors (flexibility for insertion)
        score += wAdj * instance.adj[customerId].size();

        // Add a small random perturbation to the score. This helps break ties
        // and introduces additional diversity, ensuring that even with identical
        // computed scores, the order might vary slightly across iterations.
        score += getRandomFractionFast() * 0.001f; 

        scoredCustomers.emplace_back(score, customerId);
    }

    // Sort customers in descending order based on their calculated scores
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort from highest score to lowest
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}