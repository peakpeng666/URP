#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::shuffle, std::sort
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // `currentSelectionList` stores the customers already selected in this iteration as a vector.
    // This allows for efficient random selection from the already chosen set (O(1) access)
    // to find a 'reference' customer for local expansion.
    std::vector<int> currentSelectionList; 

    // Determine the number of customers to remove.
    // This range (e.g., 10-20) is typically chosen based on the problem size (500 customers)
    // and the desired level of perturbation in each LNS iteration.
    int numCustomersToRemove = getRandomNumber(10, 20);

    // Clamp `numCustomersToRemove` to prevent trying to remove more customers than available.
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    // If no customers are available or `numCustomersToRemove` becomes 0, return an empty list.
    // However, if customers exist but `numCustomersToRemove` is 0, force removal of at least one customer
    // to ensure meaningful perturbation.
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    } else if (sol.instance.numCustomers == 0) {
        return {}; // No customers in the instance.
    }

    // Step 1: Initialize the selection with a few "seed" customers (1 to 3).
    // This helps in creating potentially disconnected removal regions, enhancing diversity across iterations.
    int numInitialSeeds = getRandomNumber(1, 3);
    for (int i = 0; i < numInitialSeeds && selectedCustomers.size() < numCustomersToRemove; ++i) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers); // Customer IDs are 1-indexed.
        if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
            selectedCustomers.insert(randomCustomer);
            currentSelectionList.push_back(randomCustomer);
        }
    }

    // Ensure at least one seed customer is added if `numCustomersToRemove` is greater than 0
    // and the initial loop somehow failed to add any (e.g., very few customers, all picked initially).
    if (currentSelectionList.empty() && numCustomersToRemove > 0 && sol.instance.numCustomers > 0) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomers.insert(randomCustomer);
        currentSelectionList.push_back(randomCustomer);
    }

    // Step 2: Iteratively expand the selection or add new random customers until the target count is reached.
    // This strategy balances focused local perturbation (by expanding from existing selections)
    // with global exploration (by occasionally adding completely random customers).
    while (selectedCustomers.size() < numCustomersToRemove) {
        // Use a random fraction to decide between local expansion (high probability)
        // and picking a new, globally random customer (low probability).
        float r = getRandomFractionFast();
        if (r < 0.85f && !currentSelectionList.empty()) { // Strategy: Local expansion (85% probability)
            // Pick a random customer from the `currentSelectionList` to act as a reference point.
            int refCustomerIdxInList = getRandomNumber(0, currentSelectionList.size() - 1);
            int refCustomer = currentSelectionList[refCustomerIdxInList];

            bool neighborAdded = false;
            // Iterate through the neighbors of the reference customer.
            // `sol.instance.adj[refCustomer]` provides a list of node IDs sorted by distance.
            // `refCustomer` (1-indexed customer ID) directly corresponds to its node index in `adj`.
            for (int neighborNode : sol.instance.adj[refCustomer]) {
                // Ensure the `neighborNode` is a customer (not the depot, which is node 0)
                // and that it's within the valid customer range (1 to `numCustomers`).
                // Also, ensure it has not been selected yet.
                if (neighborNode >= 1 && neighborNode <= sol.instance.numCustomers &&
                    selectedCustomers.find(neighborNode) == selectedCustomers.end()) {
                    selectedCustomers.insert(neighborNode);
                    currentSelectionList.push_back(neighborNode);
                    neighborAdded = true;
                    break; // Successfully added one nearest unselected neighbor. Move to the next iteration.
                }
            }
            
            // If no suitable unselected neighbor was found for the chosen `refCustomer`
            // (e.g., all neighbors were already selected or were the depot),
            // we fall back to picking a random customer to ensure progress.
            if (!neighborAdded) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
                    selectedCustomers.insert(randomCustomer);
                    currentSelectionList.push_back(randomCustomer);
                }
            }
        } else { // Strategy: Pick a completely new random customer (15% probability or if local expansion failed).
                 // This ensures continued diversity and prevents getting stuck in local regions.
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
                selectedCustomers.insert(randomCustomer);
                currentSelectionList.push_back(randomCustomer);
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Define weights for the criteria used in scoring. These can be tuned for optimal performance.
    // Prioritizing high-demand customers first in reinsertion is common, as they are often
    // harder to place due to vehicle capacity constraints.
    // Distance from the depot can also influence reinsertion order, e.g., to build routes outward.
    const float DEMAND_WEIGHT = 1000.0f; // High weight: prioritize customers with large demand.
    const float DISTANCE_FROM_DEPOT_WEIGHT = 1.0f; // Smaller weight: consider distance from depot.
    // `STOCHASTIC_PERTURBATION_FACTOR` adds randomness to scores, ensuring diversity across iterations
    // and breaking ties in a non-deterministic way.
    const float STOCHASTIC_PERTURBATION_FACTOR = 0.5f;

    // Create a vector of pairs to store (score, customer_id) for sorting.
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    // Calculate a priority score for each customer to be reinserted.
    for (int customer_id : customers) {
        // Customer IDs are 1-indexed (e.g., customer 1, 2, ..., N).
        // `instance.demand` and `instance.distanceMatrix` are 0-indexed, where index 0 is the depot.
        // Thus, `customer_id` directly maps to its data index (e.g., demand[1] for customer 1).
        
        float score = 0.0f;
        // Component 1: Demand. Higher demand leads to a higher score.
        score += static_cast<float>(instance.demand[customer_id]) * DEMAND_WEIGHT;
        // Component 2: Distance from the depot (node 0).
        // A positive weight here means customers farther from the depot get a higher score.
        score += instance.distanceMatrix[0][customer_id] * DISTANCE_FROM_DEPOT_WEIGHT;

        // Component 3: Stochastic perturbation. A small random value is added to each score.
        // This ensures that even customers with identical deterministic scores will be
        // reordered randomly, providing necessary diversity for LNS to escape local minima.
        score += getRandomFractionFast() * STOCHASTIC_PERTURBATION_FACTOR;

        scoredCustomers.push_back({score, customer_id});
    }

    // Sort the `scoredCustomers` vector in descending order of score.
    // Customers with higher scores (e.g., large demand, potentially far from the depot)
    // will be placed earlier in the reinsertion queue.
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first; // Sort by score in descending order (highest score first).
    });

    // Update the original `customers` vector with the new sorted order.
    for (size_t i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}