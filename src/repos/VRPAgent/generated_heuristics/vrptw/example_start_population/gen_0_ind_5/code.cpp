#include "AgentDesigned.h"
#include <random> 
#include <unordered_set> 
#include <algorithm> 
#include <vector> 
#include "Utils.h" 

// Function for customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove, within a specified range.
    // This introduces stochasticity in the scale of the neighborhood.
    int numCustomersToRemove = getRandomNumber(10, 20); 

    std::unordered_set<int> selectedCustomersSet; // For fast lookup of already selected customers
    std::vector<int> selectedCustomersVec;      // To store the selected customers for return value

    // Step 1: Select an initial random customer as the seed for the cluster.
    // Customers are 1-indexed in problem context (0 is depot).
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    // Step 2: Maintain a pool of customers from which to expand.
    // Initially, it contains only the seed customer. New selected customers are added to this pool.
    std::vector<int> expansionPool;
    expansionPool.push_back(initialCustomer);

    // Step 3: Iteratively expand the cluster until the target number of customers is reached.
    // Use a rotating index for the expansion pool to introduce more diversity in anchor selection,
    // rather than always expanding from the last added customer.
    int current_anchor_idx = 0;

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // Fallback if the expansion pool somehow becomes empty (e.g., all reachable customers exhausted).
        // This is highly unlikely for typical VRPTW instances with 500+ customers and small removal size.
        if (expansionPool.empty()) {
            int newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(newRandomCustomer)) { 
                newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newRandomCustomer);
            selectedCustomersVec.push_back(newRandomCustomer);
            expansionPool.push_back(newRandomCustomer); 
            continue; 
        }

        // Select an anchor customer from the expansion pool using the rotating index.
        int anchorCustomer = expansionPool[current_anchor_idx % expansionPool.size()];
        current_anchor_idx++; 

        bool foundNeighborToSelect = false;
        // Define how many of the closest neighbors to consider for expansion.
        // This limits search depth and keeps the heuristic fast.
        // It also ensures "closeness" as defined in the requirements.
        int num_neighbors_to_consider = std::min((int)sol.instance.adj[anchorCustomer].size(), 10); 

        // Collect valid, unselected neighbors from the anchor's closest neighbors.
        std::vector<int> validNeighborsFromAnchor;
        for (int i = 0; i < num_neighbors_to_consider; ++i) {
            int neighborCandidate = sol.instance.adj[anchorCustomer][i];
            // Ensure the neighbor is a customer (not depot, index > 0) and not already selected.
            if (neighborCandidate > 0 && selectedCustomersSet.find(neighborCandidate) == selectedCustomersSet.end()) {
                validNeighborsFromAnchor.push_back(neighborCandidate);
            }
        }

        // If valid neighbors are found, pick one randomly for stochastic expansion.
        if (!validNeighborsFromAnchor.empty()) {
            int chosen_neighbor_idx = getRandomNumber(0, validNeighborsFromAnchor.size() - 1);
            int chosen_neighbor = validNeighborsFromAnchor[chosen_neighbor_idx];

            selectedCustomersSet.insert(chosen_neighbor);
            selectedCustomersVec.push_back(chosen_neighbor);
            expansionPool.push_back(chosen_neighbor); 
            foundNeighborToSelect = true;
        }
    }

    return selectedCustomersVec;
}

// Function to select the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers based on a multi-criteria heuristic to prioritize reinsertion.
    // The general principle is to reinsert "harder" customers first, as they have fewer feasible positions.
    // Stochasticity is introduced by adding small random noise to float comparison values.

    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        // Noise level for float comparisons. Small enough not to change the order of clearly different values.
        float noise_level = 0.001f;

        // Primary criterion: Time Window Width (ascending -> tighter windows first)
        // Tighter windows (smaller TW_Width) mean less flexibility, making them harder to place.
        float tw1 = instance.TW_Width[c1];
        float tw2 = instance.TW_Width[c2];
        // Add random noise for stochastic tie-breaking on float values.
        tw1 += (getRandomFractionFast() - 0.5f) * noise_level;
        tw2 += (getRandomFractionFast() - 0.5f) * noise_level;

        if (tw1 != tw2) {
            return tw1 < tw2; 
        }

        // Secondary criterion: Service Time (descending -> longer service times first)
        // Longer service times consume more time on a route, potentially making them harder to fit.
        float st1 = instance.serviceTime[c1];
        float st2 = instance.serviceTime[c2];
        // Add random noise for stochastic tie-breaking.
        st1 += (getRandomFractionFast() - 0.5f) * noise_level;
        st2 += (getRandomFractionFast() - 0.5f) * noise_level;
        
        if (st1 != st2) {
            return st1 > st2; 
        }

        // Tertiary criterion: Demand (descending -> higher demand first)
        // Higher demand customers are harder to place due to vehicle capacity constraints.
        int d1 = instance.demand[c1];
        int d2 = instance.demand[c2];
        if (d1 != d2) {
            return d1 > d2; 
        }

        // Final tie-breaker: If all previous criteria are identical (or nearly identical due to noise),
        // use a purely random decision. This ensures diversity in ordering for truly equivalent customers,
        // vital for millions of iterations.
        return getRandomFractionFast() < 0.5f;
    });
}