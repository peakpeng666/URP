#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort and std::shuffle
#include <numeric>   // For std::iota if needed, though not directly used here
#include <utility>   // For std::pair

// Include Utils.h for getRandomNumber, getRandomFraction, getRandomFractionFast
#include "Utils.h"

// Heuristics for LNS framework in PCVRP

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Constants for selection strategy
    static const int LNS_NUM_CUSTOMERS_TO_REMOVE_MIN = 10;
    static const int LNS_NUM_CUSTOMERS_TO_REMOVE_MAX = 20;
    static const int LNS_MAX_NEIGHBOR_SEARCH_LIMIT = 20; // Max number of closest neighbors to consider
    static const int LNS_MAX_RANDOM_SOURCE_TRIES = 50;   // Max tries to find a new neighbor from existing selected customers

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList; // For efficient random access

    int numCustomersToRemove = getRandomNumber(LNS_NUM_CUSTOMERS_TO_REMOVE_MIN, LNS_NUM_CUSTOMERS_TO_REMOVE_MAX);

    // Step 1: Select an initial seed customer randomly
    int current_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(current_customer_id);
    selectedCustomersList.push_back(current_customer_id);

    // Step 2: Iteratively add neighbors to maintain connectivity and achieve desired size
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int next_customer_id = -1;
        
        // Try to find a new neighbor from the already selected customers
        for (int try_count = 0; try_count < LNS_MAX_RANDOM_SOURCE_TRIES; ++try_count) {
            // Pick a random customer from the currently selected ones
            int source_customer_idx = getRandomNumber(0, static_cast<int>(selectedCustomersList.size()) - 1);
            int source_customer = selectedCustomersList[source_customer_idx];

            const auto& neighbors = sol.instance.adj[source_customer];
            if (neighbors.empty()) {
                continue;
            }

            // Randomly pick a neighbor from the closest ones (up to LNS_MAX_NEIGHBOR_SEARCH_LIMIT)
            int neighbor_idx_limit = std::min(static_cast<int>(neighbors.size()), LNS_MAX_NEIGHBOR_SEARCH_LIMIT);
            if (neighbor_idx_limit == 0) { // Should not happen if neighbors is not empty
                continue;
            }
            int random_neighbor_idx = getRandomNumber(0, neighbor_idx_limit - 1);
            int candidate_neighbor = neighbors[random_neighbor_idx];

            // Ensure the candidate neighbor is not already selected
            if (selectedCustomersSet.find(candidate_neighbor) == selectedCustomersSet.end()) {
                next_customer_id = candidate_neighbor;
                break; // Found a suitable next customer
            }
        }

        // Fallback: If no suitable neighbor found after multiple tries (unlikely for dense instances)
        // or if the initially selected customers have no unselected neighbors,
        // select a completely random unselected customer. This ensures the target count is always met.
        if (next_customer_id == -1) {
            do {
                next_customer_id = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.find(next_customer_id) != selectedCustomersSet.end());
        }
        
        selectedCustomersSet.insert(next_customer_id);
        selectedCustomersList.push_back(next_customer_id);
    }

    return selectedCustomersList;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Constants for sorting strategy
    static const float LNS_SORT_PRIZE_FACTOR = 1.0f;        // Weight for customer prize
    static const float LNS_SORT_DIST_DEPOT_FACTOR = 0.01f;  // Weight for inverse distance to depot (penalize far customers)
    static const float LNS_SORT_NOISE_FACTOR = 0.1f;        // Amount of random noise to introduce for diversity

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float score = 0.0f;

        // Add customer prize to score (higher prize = higher score)
        score += instance.prizes[customer_id] * LNS_SORT_PRIZE_FACTOR;

        // Subtract distance to depot (closer to depot = higher score)
        // Assuming depot is node 0, and distanceMatrix is indexed 0 to numNodes-1
        score -= instance.distanceMatrix[0][customer_id] * LNS_SORT_DIST_DEPOT_FACTOR;

        // Add stochastic noise to ensure diversity over millions of iterations
        score += getRandomFraction(0.0f, 1.0f) * LNS_SORT_NOISE_FACTOR;

        scored_customers.push_back({score, customer_id});
    }

    // Sort customers in descending order of their calculated score
    // Customers with higher scores will be placed earlier in the vector
    std::sort(scored_customers.begin(), scored_customers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}