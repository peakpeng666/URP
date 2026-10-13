#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::min
#include "Utils.h"

// Constants for select_by_llm_1
// Defines the minimum and maximum number of customers to be removed in each LNS iteration.
// This range is kept small to focus the search and ensure fast reinsertion.
const int MIN_REMOVE_COUNT = 8;
const int MAX_REMOVE_COUNT = 15;

// Probability for adding a completely random customer during selection.
// This helps to break out of local clusters and explore diverse solution spaces.
const float P_RANDOM_CUSTOMER_ADD = 0.15;

// Probability to bias selection towards unvisited customers.
// This ensures that unserved customers get a chance to be included in the solution.
const float P_UNVISITED_BIAS_ADD = 0.3;

// Maximum number of closest neighbors to consider when expanding a cluster.
// Limiting this keeps the selection fast and focuses on immediate vicinity.
const int MAX_NEIGHBORS_TO_EXPLORE = 5;

// Decay factor for neighbor selection probability.
// Closer neighbors have a higher chance of being selected, but farther ones are still possible.
// Probability for neighbor `i` is `NEIGHBOR_SELECTION_DECAY / (i + 1.0)`.
const float NEIGHBOR_SELECTION_DECAY = 0.8;

// Constants for sort_by_llm_1
// Weights for calculating customer desirability score for reinsertion order.
// Higher prize is more desirable.
const float PRIZE_WEIGHT = 1.0;
// Higher demand penalizes desirability (harder to fit).
const float DEMAND_PENALTY = 0.1;
// Greater distance from depot penalizes desirability (higher travel cost).
const float DEPOT_DIST_PENALTY = 0.01;
// Factor for adding random noise to scores, ensuring stochasticity in sorting.
const float RANDOM_NOISE_FACTOR = 0.05;

// select_by_llm_1: Heuristic for selecting customers to remove.
// This function aims to select a small, mostly clustered group of customers,
// while also ensuring stochasticity and considering unvisited customers.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers_set;
    // `candidate_pool` stores customers that can be used as anchor points
    // for selecting new customers based on proximity.
    std::vector<int> candidate_pool;

    // Determine the number of customers to remove for this iteration.
    int numCustomersToRemove = getRandomNumber(MIN_REMOVE_COUNT, MAX_REMOVE_COUNT);

    // Step 1: Initialize the selection with a random seed customer.
    // This ensures a diverse starting point for the cluster expansion.
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers_set.insert(initial_seed);
    candidate_pool.push_back(initial_seed);

    // Step 2: Iteratively select customers until the target count is reached.
    while (selectedCustomers_set.size() < numCustomersToRemove) {
        int next_customer_to_add = -1;

        // Strategy A: Probabilistically try to select an unvisited customer.
        // This ensures the LNS can try to incorporate previously unserved customers.
        if (getRandomFraction() < P_UNVISITED_BIAS_ADD) {
            std::vector<int> unvisited_candidates;
            for (int c = 1; c <= sol.instance.numCustomers; ++c) {
                // Check if customer is unvisited and not already selected for removal.
                if (sol.customerToTourMap[c] == -1 && selectedCustomers_set.find(c) == selectedCustomers_set.end()) {
                    unvisited_candidates.push_back(c);
                }
            }
            if (!unvisited_candidates.empty()) {
                next_customer_to_add = unvisited_candidates[getRandomNumber(0, unvisited_candidates.size() - 1)];
            }
        }

        // Strategy B: If no unvisited customer was selected or available,
        // attempt to add a neighbor of an already selected customer (cluster expansion).
        if (next_customer_to_add == -1) {
            int anchor_customer = -1;
            // Pick a random customer from the `candidate_pool` to serve as an anchor.
            if (!candidate_pool.empty()) {
                anchor_customer = candidate_pool[getRandomNumber(0, candidate_pool.size() - 1)];
            } else {
                // Fallback: If candidate pool is empty (e.g., very small initial selection),
                // pick a completely random customer.
                anchor_customer = getRandomNumber(1, sol.instance.numCustomers);
            }

            // Iterate through the closest neighbors of the anchor customer.
            for (int i = 0; i < std::min((int)sol.instance.adj[anchor_customer].size(), MAX_NEIGHBORS_TO_EXPLORE); ++i) {
                int neighbor_id = sol.instance.adj[anchor_customer][i];
                // Only consider neighbors not already selected for removal.
                if (selectedCustomers_set.find(neighbor_id) == selectedCustomers_set.end()) {
                    // Probabilistically select the neighbor, favoring closer ones (smaller `i`).
                    if (getRandomFraction() < (NEIGHBOR_SELECTION_DECAY / (i + 1.0))) {
                        next_customer_to_add = neighbor_id;
                        break; // A neighbor was selected, move to the next step.
                    }
                }
            }
        }

        // Strategy C: Fallback or Global Diversification
        // If no specific customer was selected by Strategies A or B,
        // or with a small probability (for global diversity), add a completely random customer.
        if (next_customer_to_add == -1 || getRandomFraction() < P_RANDOM_CUSTOMER_ADD) {
            next_customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
            // Ensure the randomly selected customer is unique.
            // This loop is safe for small `numCustomersToRemove` relative to `numCustomers`.
            while (selectedCustomers_set.find(next_customer_to_add) != selectedCustomers_set.end()) {
                next_customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
            }
        }
        
        // Add the determined customer to the set of selected customers and the candidate pool.
        selectedCustomers_set.insert(next_customer_to_add);
        candidate_pool.push_back(next_customer_to_add);
    }

    // Convert the set of selected customers to a vector for return.
    return std::vector<int>(selectedCustomers_set.begin(), selectedCustomers_set.end());
}

// sort_by_llm_1: Heuristic for ordering the removed customers for reinsertion.
// This function sorts customers based on a desirability score, prioritizing
// those that are most valuable or potentially easier/more profitable to reinsert.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Calculate a desirability score for each customer.
    // The score combines prize, demand, and distance from the depot, plus random noise.
    std::vector<float> scores(customers.size());
    for (size_t i = 0; i < customers.size(); ++i) {
        int customer_id = customers[i];
        scores[i] = (instance.prizes[customer_id] * PRIZE_WEIGHT) -
                    (instance.demand[customer_id] * DEMAND_PENALTY) -
                    (instance.distanceMatrix[0][customer_id] * DEPOT_DIST_PENALTY) +
                    (getRandomFractionFast() * RANDOM_NOISE_FACTOR);
    }

    // Use argsort to get the indices that would sort the `scores` vector in ascending order.
    std::vector<int> sorted_indices = argsort(scores);

    // Reorder the `customers` vector based on the sorted indices.
    // We want customers with higher scores (more desirable) to appear earlier in the vector.
    // `argsort` returns indices for ascending order, so we iterate its result in reverse
    // to achieve descending order of scores for our `customers` vector.
    std::vector<int> temp_customers = customers; // Create a temporary copy to facilitate reordering
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = temp_customers[sorted_indices[customers.size() - 1 - i]];
    }
}