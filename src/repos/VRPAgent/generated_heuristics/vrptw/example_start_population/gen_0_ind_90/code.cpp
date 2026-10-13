#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> 
#include <vector>
#include <limits> 

#include "Utils.h" 

// Define thread_local random number generators for stochastic functions
// These generators ensure independent random sequences for selection and sorting,
// and are thread-safe if the LNS framework runs in a multi-threaded environment.
static thread_local std::mt19937 select_rng(std::random_device{}());
static thread_local std::mt19937 sort_rng(std::random_device{}());


// Heuristic for Customer Removal: select_by_llm_1
// This function selects a subset of customers to remove from the current solution.
// The goal is to select customers that are spatially related (close to each other)
// to facilitate meaningful reinsertion, while incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove stochastically.
    // A range of 15 to 30 customers provides a good balance between perturbation size
    // and maintaining problem structure for large instances (500+ customers).
    int min_customers_to_remove = 15;
    int max_customers_to_remove = 30;
    std::uniform_int_distribution<> num_dist(min_customers_to_remove, max_customers_to_remove);
    int numCustomersToRemove = num_dist(select_rng);

    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> potential_expansion_points; // Stores selected customers from which to expand the "cluster"

    // 1. Pick a random seed customer to initiate the selection process.
    // Customer IDs are typically 1 to numCustomers, with 0 being the depot.
    std::uniform_int_distribution<> customer_dist(1, sol.instance.numCustomers);
    int initial_seed = customer_dist(select_rng);
    selectedCustomers_set.insert(initial_seed);
    potential_expansion_points.push_back(initial_seed);

    // 2. Iteratively expand the selection until the target number of customers is reached.
    // The expansion is biased towards customers close to already selected ones.
    while (selectedCustomers_set.size() < numCustomersToRemove) {
        // If all potential expansion points have been exhausted (unlikely for dense instances
        // and small removal sizes, but a safeguard), randomly pick another unselected customer.
        if (potential_expansion_points.empty()) {
            int fallback_customer = -1;
            int max_attempts = 100; // Limit attempts to find an unselected customer
            for (int i = 0; i < max_attempts; ++i) {
                int c = customer_dist(select_rng);
                if (selectedCustomers_set.find(c) == selectedCustomers_set.end()) {
                    fallback_customer = c;
                    break;
                }
            }
            if (fallback_customer != -1) {
                selectedCustomers_set.insert(fallback_customer);
                potential_expansion_points.push_back(fallback_customer);
            } else {
                // If no new customer can be found (e.g., all customers selected or very small problem), break.
                break;
            }
            continue; // Continue to the next iteration to try expanding from the new point.
        }

        // Randomly select an existing customer from the `potential_expansion_points` list.
        // This ensures the "cluster" can grow from different parts, adding diversity to its shape.
        std::uniform_int_distribution<> exp_point_dist(0, potential_expansion_points.size() - 1);
        int current_expansion_point_idx = exp_point_dist(select_rng);
        int current_expansion_point = potential_expansion_points[current_expansion_point_idx];

        // Access the pre-sorted (by distance) adjacency list for the current expansion point.
        const auto& neighbors = sol.instance.adj[current_expansion_point];
        bool added_new_customer_in_this_iter = false;

        // Consider only a limited number of the closest neighbors for efficiency.
        int num_neighbors_to_check = std::min((int)neighbors.size(), 15); 

        // Shuffle the subset of closest neighbors to introduce more randomness in the selection order.
        std::vector<int> neighbors_subset(neighbors.begin(), neighbors.begin() + num_neighbors_to_check);
        std::shuffle(neighbors_subset.begin(), neighbors_subset.end(), select_rng);

        // Iterate through the shuffled neighbors and add the first suitable (unselected) one.
        for (int neighbor_customer : neighbors_subset) {
            if (neighbor_customer != 0 && selectedCustomers_set.find(neighbor_customer) == selectedCustomers_set.end()) {
                selectedCustomers_set.insert(neighbor_customer);
                potential_expansion_points.push_back(neighbor_customer); // The newly added customer can also be an expansion point.
                added_new_customer_in_this_iter = true;
                break; // Add only one new customer per main loop iteration to control growth.
            }
        }

        // If no new customer was added from the current expansion point (e.g., all its closest neighbors were already selected),
        // remove it from the list of potential expansion points to avoid repeatedly checking it.
        if (!added_new_customer_in_this_iter) {
            potential_expansion_points.erase(potential_expansion_points.begin() + current_expansion_point_idx);
        }
    }

    // Convert the set of selected customers to a vector for return.
    return std::vector<int>(selectedCustomers_set.begin(), selectedCustomers_set.end());
}


// Heuristic for Customer Ordering: sort_by_llm_1
// This function determines the order in which the removed customers will be reinserted.
// A good order can significantly impact the effectiveness of the greedy reinsertion step.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<int> sorted_customers;
    std::unordered_set<int> remaining_customers_set(customers.begin(), customers.end());

    // 1. Choose a random starting customer from the set of removed customers.
    // This adds stochasticity to the beginning of the reinsertion chain.
    std::uniform_int_distribution<> start_cust_dist(0, customers.size() - 1);
    int current_customer_in_chain = customers[start_cust_dist(sort_rng)];

    sorted_customers.push_back(current_customer_in_chain);
    remaining_customers_set.erase(current_customer_in_chain);

    // 2. Build a "chain" by iteratively selecting the next customer.
    // The selection prioritizes customers close to the `current_customer_in_chain`,
    // while also introducing stochasticity to explore diverse reinsertion paths.
    while (!remaining_customers_set.empty()) {
        std::vector<std::pair<float, int>> potential_next_customers;
        for (int c : remaining_customers_set) {
            potential_next_customers.push_back({instance.distanceMatrix[current_customer_in_chain][c], c});
        }

        // Sort the remaining customers by their distance to the current customer in ascending order.
        std::sort(potential_next_customers.begin(), potential_next_customers.end());

        // Introduce stochasticity by selecting from the top few closest candidates.
        // This prevents deterministic behavior while still favoring proximity.
        int num_closest_to_consider = std::min((int)potential_next_customers.size(), 7); 

        // Assign weights to the top candidates: closer customers (smaller index) get higher weights.
        // This creates a biased probability distribution, making closer customers more likely to be chosen.
        std::vector<float> weights(num_closest_to_consider);
        float total_weight = 0.0f;
        for (int i = 0; i < num_closest_to_consider; ++i) {
            weights[i] = static_cast<float>(num_closest_to_consider - i); // Example: if 7 considered, weights are 7, 6, ..., 1.
            total_weight += weights[i];
        }

        // Randomly select a candidate based on the calculated weights.
        std::uniform_real_distribution<> weight_dist(0.0, total_weight);
        float rand_val = weight_dist(sort_rng);
        int selected_idx = 0;
        for (int i = 0; i < num_closest_to_consider; ++i) {
            rand_val -= weights[i];
            if (rand_val <= 0) {
                selected_idx = i;
                break;
            }
        }
        // Ensure the selected index is within bounds.
        selected_idx = std::min(selected_idx, num_closest_to_consider - 1);

        int next_customer_to_add = potential_next_customers[selected_idx].second;

        sorted_customers.push_back(next_customer_to_add);
        remaining_customers_set.erase(next_customer_to_add);
        current_customer_in_chain = next_customer_to_add; // Advance the chain to the newly added customer.
    }

    // Assign the newly sorted list back to the input vector.
    customers = sorted_customers;
}