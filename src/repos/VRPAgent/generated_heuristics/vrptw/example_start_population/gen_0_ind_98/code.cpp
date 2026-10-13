#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// --- Heuristic for Customer Selection (Step 1) ---
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Parameters for the removal heuristic
    // The number of customers to remove in each iteration.
    // Random range ensures diversity in neighborhood size.
    const int MIN_CUSTOMERS_TO_REMOVE = 15;
    const int MAX_CUSTOMERS_TO_REMOVE = 30;

    // Probability of attempting to add a customer from the neighborhood of an already selected customer.
    // Higher values promote "clustered" removals. Lower values promote more dispersed removals.
    const float P_NEIGHBORHOOD_ADD_BIAS = 0.75f; // 75% chance to pick from neighborhood

    // The number of nearest neighbors to check from the adjacency list (adj) of a pivot customer.
    // Adj lists are pre-sorted by distance. Checking only the closest ones for speed.
    const size_t K_NEIGHBORS_TO_CHECK = 15;

    std::unordered_set<int> removed_set; // Use a hash set for O(1) average time complexity for insertions and lookups
    std::vector<int> removed_list;       // Use a vector to quickly pick a random pivot from the selected customers

    int num_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    // Step 1: Select an initial random customer as a seed
    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    removed_set.insert(initial_customer);
    removed_list.push_back(initial_customer);

    // Step 2: Iteratively add customers based on a mix of neighborhood proximity and global randomness
    while (removed_set.size() < num_to_remove) {
        int customer_to_add = -1;
        bool candidate_found = false;

        // With a certain probability, attempt to add a customer from the neighborhood of an already selected one.
        if (getRandomFractionFast() < P_NEIGHBORHOOD_ADD_BIAS && !removed_list.empty()) {
            // Pick a random customer from the currently selected set to act as a pivot.
            int pivot_idx = getRandomNumber(0, static_cast<int>(removed_list.size() - 1));
            int pivot_customer = removed_list[pivot_idx];

            // Iterate through the pivot's nearest neighbors (from the pre-sorted adj list).
            const std::vector<int>& neighbors = sol.instance.adj[pivot_customer];
            for (size_t i = 0; i < neighbors.size() && i < K_NEIGHBORS_TO_CHECK; ++i) {
                int current_neighbor = neighbors[i];
                // Check if the neighbor is not already in the removed set.
                if (removed_set.find(current_neighbor) == removed_set.end()) {
                    customer_to_add = current_neighbor;
                    candidate_found = true;
                    break; // Found a suitable neighbor, add it.
                }
            }
        }

        // If no candidate was found through neighborhood search (either due to probability or no suitable neighbors),
        // or if the initial bias was not met, fall back to picking a completely random customer.
        if (!candidate_found) {
            int attempts = 0;
            const int MAX_RANDOM_ATTEMPTS = 100; // Limit attempts to avoid infinite loops in edge cases
            while (attempts < MAX_RANDOM_ATTEMPTS) {
                int rand_customer = getRandomNumber(1, sol.instance.numCustomers);
                // Ensure the randomly picked customer is not already in the removed set.
                if (removed_set.find(rand_customer) == removed_set.end()) {
                    customer_to_add = rand_customer;
                    candidate_found = true;
                    break;
                }
                attempts++;
            }
            // In extremely rare cases (e.g., if num_to_remove is close to total customers and many attempts fail),
            // candidate_found might still be false here. The loop structure assumes it will eventually find one.
        }

        // If a customer was identified, add it to both the set and the list.
        if (candidate_found) {
            removed_set.insert(customer_to_add);
            removed_list.push_back(customer_to_add);
        }
    }

    return std::vector<int>(removed_set.begin(), removed_set.end());
}

// --- Heuristic for Ordering of Removed Customers (Step 3) ---
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // This function sorts the removed customers for reinsertion.
    // The goal is to prioritize "harder" customers first, as they might have fewer feasible insertion points.
    // Stochasticity is added to ensure diversity over many iterations.

    // Constants for weighting different customer characteristics.
    // These weights influence the primary sorting criteria.
    // Adjusting these can change the heuristic's behavior.
    const float TIME_WINDOW_WIDTH_WEIGHT = 1000.0f; // Prioritize tighter time windows (smaller width)
    const float SERVICE_TIME_WEIGHT = -1.0f;        // Prioritize longer service times (larger value, hence negative weight for asc sort)
    const float DISTANCE_FROM_DEPOT_WEIGHT = -0.1f; // Prioritize customers further from depot (larger distance, hence negative weight for asc sort)

    // Epsilon for adding stochastic noise to the sort key.
    // A small value ensures that primary criteria dominate, but ties are broken randomly.
    const float EPSILON_NOISE = 0.001f;

    // Create a vector of pairs: {sort_key, customer_id}
    // This allows sorting by the custom sort_key while retaining the original customer IDs.
    std::vector<std::pair<float, int>> customer_sort_data;
    customer_sort_data.reserve(customers.size());

    for (int customer_id : customers) {
        // Calculate a combined sort key based on multiple customer characteristics.
        // The goal is to make "harder" customers (e.g., tight TW, long service, far from depot) have a lower sort key
        // when sorting in ascending order.
        float sort_key = (instance.TW_Width[customer_id] * TIME_WINDOW_WIDTH_WEIGHT) +
                         (instance.serviceTime[customer_id] * SERVICE_TIME_WEIGHT) +
                         (instance.distanceMatrix[0][customer_id] * DISTANCE_FROM_DEPOT_WEIGHT);

        // Add a small random perturbation to the sort key to introduce stochasticity.
        // This is crucial for exploring diverse reinsertion orders over many iterations,
        // especially for customers with very similar characteristics.
        sort_key += getRandomFractionFast() * EPSILON_NOISE;

        customer_sort_data.push_back({sort_key, customer_id});
    }

    // Sort the customer_sort_data vector based on the calculated sort_key in ascending order.
    // This places customers with lower sort_keys (i.e., "harder" customers) at the beginning.
    std::sort(customer_sort_data.begin(), customer_sort_data.end());

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customer_sort_data.size(); ++i) {
        customers[i] = customer_sort_data[i].second;
    }
}