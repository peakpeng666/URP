#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort, std::min
#include <vector>
#include <limits> // For std::numeric_limits
#include "Utils.h"

// Define constants for heuristic parameters to allow easier tuning
// For select_by_llm_1
const int MIN_CUSTOMERS_TO_REMOVE = 15;
const int MAX_CUSTOMERS_TO_REMOVE = 30;
const int MAX_NEIGHBORS_TO_CHECK = 10; // Limit for checking closest neighbors for expansion
const int NEW_SEED_ATTEMPTS_LIMIT = 100; // Max attempts to find a new seed if cluster expansion fails

// For sort_by_llm_1
// Weights for reinsertion priority components
const float SORT_WEIGHT_PRIZE = 0.4f;
const float SORT_WEIGHT_DEMAND_PENALTY = 0.3f;
const float SORT_WEIGHT_CONNECTIVITY_BONUS = 0.2f;
const float SORT_WEIGHT_RANDOM_PERTURBATION = 0.1f;
const float EPSILON = 1e-6f; // Small value to prevent division by zero by zero

// Customer selection: selects a connected-like cluster of customers for removal
std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    
    std::unordered_set<int> selected_customers_set;
    std::vector<int> expansion_candidates; // Customers already selected, from which we can expand

    // 1. Initial Seed Selection
    // Pick a random customer from all possible customers (1 to numCustomers)
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_seed);
    expansion_candidates.push_back(initial_seed);

    // 2. Iterative Expansion to form a 'cluster'
    while (selected_customers_set.size() < num_to_remove) {
        if (expansion_candidates.empty()) {
            // Fallback: If all current expansion candidates are exhausted (i.e., all their
            // neighbors are already selected or they have no neighbors), pick a new random
            // customer not yet selected as a new seed. This ensures we always try to meet num_to_remove.
            int new_seed = -1;
            for (int attempt = 0; attempt < NEW_SEED_ATTEMPTS_LIMIT; ++attempt) {
                int potential_new_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(potential_new_seed) == selected_customers_set.end()) {
                    new_seed = potential_new_seed;
                    break;
                }
            }
            
            if (new_seed != -1) {
                selected_customers_set.insert(new_seed);
                expansion_candidates.push_back(new_seed);
            } else {
                // Cannot find enough customers to form the desired removal set.
                // This scenario is highly unlikely for large instances (500+ customers)
                // but good to have a safeguard.
                break; 
            }
        }

        // Pick a random pivot customer from the current expansion_candidates
        int pivot_idx_in_candidates = getRandomNumber(0, expansion_candidates.size() - 1);
        int pivot_customer = expansion_candidates[pivot_idx_in_candidates];

        std::vector<int> potential_additions;
        // Iterate through the closest neighbors of the pivot customer
        // The adj list is pre-sorted by distance, so first elements are closest.
        int num_neighbors_to_check = std::min((int)sol.instance.adj[pivot_customer].size(), MAX_NEIGHBORS_TO_CHECK);
        
        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor = sol.instance.adj[pivot_customer][i];
            // Ensure neighbor is a customer (1 to numCustomers, not depot 0)
            if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && 
                selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                potential_additions.push_back(neighbor);
            }
        }

        if (!potential_additions.empty()) {
            // Add a random available neighbor to the set
            int customer_to_add = potential_additions[getRandomNumber(0, potential_additions.size() - 1)];
            selected_customers_set.insert(customer_to_add);
            expansion_candidates.push_back(customer_to_add);
        } else {
            // If no new neighbors were found from this pivot, remove it from candidates
            // to avoid re-picking a 'dead end'. O(1) swap-and-pop for vector.
            if (expansion_candidates.size() > 1) {
                expansion_candidates[pivot_idx_in_candidates] = expansion_candidates.back();
                expansion_candidates.pop_back();
            } else { // Only one element left and it's exhausted
                expansion_candidates.clear();
            }
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}


// Ordering of the removed customers for reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Pair of (reinsertion_priority, customer_id)
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Calculate a priority score for each customer
    for (int customer_id : customers) {
        float score = 0.0f;

        // Component 1: Prize value (higher prize = higher priority)
        score += instance.prizes[customer_id] * SORT_WEIGHT_PRIZE;

        // Component 2: Demand penalty (higher demand = lower priority, normalized)
        // Scale the penalty relative to the total possible prize or a sensible range
        float demand_norm = (float)instance.demand[customer_id] / instance.vehicleCapacity;
        score -= demand_norm * (instance.total_prizes * 0.05f) * SORT_WEIGHT_DEMAND_PENALTY; // Scale by a fraction of total prizes

        // Component 3: Connectivity bonus (closer to other nodes = higher priority)
        // Using the closest neighbor distance from the pre-computed adj list (node 0 is depot)
        if (!instance.adj[customer_id].empty()) {
            float closest_dist = instance.distanceMatrix[customer_id][instance.adj[customer_id][0]];
            // Invert distance to represent 'closeness'. Scale by a fraction of total prizes.
            score += (1.0f / (closest_dist + EPSILON)) * (instance.total_prizes * 0.001f) * SORT_WEIGHT_CONNECTIVITY_BONUS;
        } else {
            // If a customer has no neighbors (e.g., very isolated), it receives no bonus from this term.
        }

        // Component 4: Stochastic perturbation for diversity over iterations
        // Add random noise centered around 0 to perturb the scores slightly
        score += (getRandomFractionFast() - 0.5f) * (instance.total_prizes * 0.002f) * SORT_WEIGHT_RANDOM_PERTURBATION;

        scored_customers.push_back({score, customer_id});
    }

    // Sort customers based on their scores in descending order
    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort in descending order of score
    });

    // Update the original 'customers' vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}