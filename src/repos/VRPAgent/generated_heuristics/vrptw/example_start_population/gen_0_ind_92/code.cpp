#include "AgentDesigned.h" // Assumed to include Solution.h, Instance.h, Tour.h
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// Define constants for customer removal.
// For 500 customers, removing 2-4% (10-20 customers) is a reasonable range
// that allows for significant solution perturbation without being too disruptive
// for the LNS framework, given that the search is limited by runtime.
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;

// Define constants for customer reinsertion ordering.
// These weights determine the importance of different factors when prioritizing
// customers for reinsertion. Time window tightness is often the most critical
// constraint in VRPTW.
const float W_TW_TIGHTNESS = 0.6f;     // Weight for time window tightness (higher for tighter windows)
const float W_DEMAND       = 0.2f;     // Weight for customer demand
const float W_SERVICE      = 0.2f;     // Weight for service time
const float W_STOCHASTICITY = 0.001f;  // Small noise to break ties and add diversity for millions of iterations

// Epsilon value used to prevent division by zero for very small time window widths
// and to provide a stable base for the inverse time window tightness score.
const float EPSILON = 0.1f;

// Step 1: Customer Selection Heuristic (`select_by_llm_1`)
// This heuristic selects a subset of customers for removal. It aims to select
// customers that are "close" to each other to encourage meaningful local
// perturbations, while incorporating stochasticity to ensure diversity across
// LNS iterations.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers;
    std::vector<int> candidate_pool_for_expansion; // Customers already selected, from which we can expand

    // Determine the number of customers to remove for this iteration.
    int num_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    // Phase 1: Initial seed selection.
    // Start the cluster by randomly picking one customer. This ensures stochasticity
    // in the starting point of each removal operation.
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers.insert(initial_seed);
    candidate_pool_for_expansion.push_back(initial_seed);

    // Phase 2: Iterative cluster expansion.
    // Grow the cluster by iteratively adding closest unselected neighbors of
    // already selected customers. This ensures the removed customers are spatially
    // related, while randomness in pivot selection adds diversity.
    while (selected_customers.size() < num_to_remove) {
        // If the expansion pool becomes empty, it means the current cluster is
        // isolated or exhausted. Pick another random seed to continue.
        if (candidate_pool_for_expansion.empty()) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            if (selected_customers.find(new_seed) == selected_customers.end()) { // Avoid re-adding existing
                selected_customers.insert(new_seed);
                candidate_pool_for_expansion.push_back(new_seed);
            }
            // If the new seed was already selected, the loop will continue to try finding a non-selected one.
            // In very rare cases (all customers selected), this could infinite loop without a safeguard,
            // but for typical small `num_to_remove` this is not an issue.
            if (selected_customers.size() == num_to_remove) break; // Check if we just hit target with new seed
            continue; // Re-start loop to use the newly added seed
        }

        // Randomly pick a customer from the current `candidate_pool_for_expansion`.
        // This customer acts as a pivot from which to expand the cluster.
        int rand_idx_in_pool = getRandomNumber(0, candidate_pool_for_expansion.size() - 1);
        int current_pivot_customer = candidate_pool_for_expansion[rand_idx_in_pool];

        bool added_new_customer = false;
        // Limit the number of neighbors checked to maintain speed, typically 10-20 closest neighbors are sufficient.
        const int MAX_NEIGHBORS_TO_CHECK = 15;
        int neighbors_checked = 0;

        // Iterate through the pivot's neighbors (pre-sorted by distance in `instance.adj`).
        for (int neighbor_id : sol.instance.adj[current_pivot_customer]) {
            // Ensure the neighbor is a valid customer ID (not depot, within customer range).
            if (neighbor_id > 0 && neighbor_id <= sol.instance.numCustomers) {
                // If this neighbor is not already selected for removal, add it.
                if (selected_customers.find(neighbor_id) == selected_customers.end()) {
                    selected_customers.insert(neighbor_id);
                    candidate_pool_for_expansion.push_back(neighbor_id); // Add to pool for further expansion
                    added_new_customer = true;
                    break; // Stop after adding one new customer from this pivot
                }
            }
            neighbors_checked++;
            if (neighbors_checked >= MAX_NEIGHBORS_TO_CHECK) {
                break; // Stop checking further if max neighbors limit reached
            }
        }

        // If no new customer was added from the `current_pivot_customer` (e.g., all its
        // closest neighbors are already selected or invalid), remove it from the
        // expansion pool to avoid getting stuck on unproductive pivots.
        if (!added_new_customer) {
            candidate_pool_for_expansion[rand_idx_in_pool] = candidate_pool_for_expansion.back();
            candidate_pool_for_expansion.pop_back();
        }
    }

    // Convert the set of selected customers to a vector for return.
    return std::vector<int>(selected_customers.begin(), selected_customers.end());
}


// Step 3: Customer Ordering Heuristic (`sort_by_llm_1`)
// This heuristic determines the order in which removed customers are reinserted
// into the solution. It prioritizes customers that are "more difficult" to place,
// typically those with tighter time windows, higher demand, or longer service times.
// This allows the greedy reinsertion mechanism to tackle the most constrained
// customers first.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // A vector to store pairs of (priority_score, customer_id).
    // The negative of the score is stored to allow `std::sort` (ascending)
    // to effectively sort customers in descending order of priority.
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size()); // Pre-allocate memory for efficiency

    for (int customer_id : customers) {
        // Calculate a score for time window tightness. Tighter windows (smaller width)
        // result in a higher `tw_tightness_score`.
        float tw_tightness_score = 1.0f / (instance.TW_Width[customer_id] + EPSILON);

        // Retrieve demand and service time scores directly from instance data.
        float demand_score = static_cast<float>(instance.demand[customer_id]);
        float service_score = instance.serviceTime[customer_id];

        // Combine the scores using predefined weights.
        // A small random component (`getRandomFractionFast() * W_STOCHASTICITY`)
        // is added to introduce slight variations, breaking ties and contributing
        // to exploration over millions of LNS iterations.
        float total_score = (tw_tightness_score * W_TW_TIGHTNESS +
                             demand_score * W_DEMAND +
                             service_score * W_SERVICE) +
                            (getRandomFractionFast() * W_STOCHASTICITY);

        // Store the negative total_score along with the customer ID.
        scored_customers.push_back({-total_score, customer_id});
    }

    // Sort the customers based on their calculated scores. Because negative scores
    // were stored, this `std::sort` (which sorts in ascending order) will effectively
    // arrange customers from highest priority (most "difficult") to lowest priority.
    std::sort(scored_customers.begin(), scored_customers.end());

    // Update the original `customers` vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}