#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::find
#include <vector>
#include "Utils.h"

// Heuristic for Step 1: Customer Selection
// Goal: Select a subset of customers to remove.
// This heuristic aims to select customers that are somewhat clustered, either spatially
// or within existing tours, while incorporating stochasticity.
// It uses a "seed and expand" approach.
std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    std::unordered_set<int> selectedCustomers;
    std::vector<int> customerPool; // Customers whose neighbors we might explore

    // Determine the number of customers to remove dynamically.
    // This provides a scalable range based on the total number of customers.
    int min_customers_to_remove = std::max(5, (int)(instance.numCustomers * 0.03));
    int max_customers_to_remove = std::min(instance.numCustomers, (int)(instance.numCustomers * 0.07));
    
    // Ensure min is not greater than max, and handle edge cases for very small instances.
    if (max_customers_to_remove < min_customers_to_remove) {
        max_customers_to_remove = min_customers_to_remove;
    }
    if (min_customers_to_remove == 0 && instance.numCustomers > 0) { // Ensure at least 1 customer removed for non-empty instances
        min_customers_to_remove = 1;
        max_customers_to_remove = std::max(1, max_customers_to_remove);
    }
    
    int numCustomersToRemove = getRandomNumber(min_customers_to_remove, max_customers_to_remove);

    if (numCustomersToRemove == 0 || instance.numCustomers == 0) {
        return {}; // No customers to remove or no customers in instance
    }

    // Probability for a neighbor to be included in the selection/pool
    const float inclusion_probability = 0.7f;
    // Maximum number of closest spatial neighbors to consider from instance.adj
    const int max_spatial_neighbors_to_consider = 5;

    // 1. Seed the selection process: Pick a random customer.
    int initial_seed_customer = getRandomNumber(1, instance.numCustomers);
    selectedCustomers.insert(initial_seed_customer);
    customerPool.push_back(initial_seed_customer);

    // 2. Expand the selection by exploring neighbors of customers already in the pool.
    size_t pool_idx = 0; // Index to iterate through customerPool
    while (selectedCustomers.size() < numCustomersToRemove && pool_idx < customerPool.size()) {
        int current_pivot_customer = customerPool[pool_idx++];

        // A. Consider neighbors within the current tour of the pivot customer.
        int tour_idx = sol.customerToTourMap[current_pivot_customer];
        // Ensure the tour_idx is valid and corresponds to an existing tour
        if (tour_idx != -1 && tour_idx < sol.tours.size()) {
            const Tour& tour = sol.tours[tour_idx];
            auto it = std::find(tour.customers.begin(), tour.customers.end(), current_pivot_customer);
            if (it != tour.customers.end()) {
                // Add preceding customer in tour (if exists)
                if (it != tour.customers.begin()) {
                    int neighbor = *std::prev(it);
                    if (selectedCustomers.find(neighbor) == selectedCustomers.end() && getRandomFractionFast() < inclusion_probability) {
                        selectedCustomers.insert(neighbor);
                        customerPool.push_back(neighbor);
                        if (selectedCustomers.size() == numCustomersToRemove) break;
                    }
                }
                // Add succeeding customer in tour (if exists)
                if (std::next(it) != tour.customers.end()) {
                    int neighbor = *std::next(it);
                    if (selectedCustomers.find(neighbor) == selectedCustomers.end() && getRandomFractionFast() < inclusion_probability) {
                        selectedCustomers.insert(neighbor);
                        customerPool.push_back(neighbor);
                        if (selectedCustomers.size() == numCustomersToRemove) break;
                    }
                }
            }
        }

        // B. Consider spatially closest neighbors using instance.adj.
        // instance.adj[customer_id] contains a list of nearest nodes (including depot at index 0).
        const std::vector<int>& adj_list = instance.adj[current_pivot_customer];
        int neighbors_considered_from_adj = 0;
        for (int neighbor_node_id : adj_list) {
            // Skip depot (0) or invalid customer IDs
            if (neighbor_node_id == 0 || neighbor_node_id > instance.numCustomers) continue;
            
            // Only consider if not already selected
            if (selectedCustomers.find(neighbor_node_id) == selectedCustomers.end()) {
                if (getRandomFractionFast() < inclusion_probability) {
                    selectedCustomers.insert(neighbor_node_id);
                    customerPool.push_back(neighbor_node_id);
                    if (selectedCustomers.size() == numCustomersToRemove) break;
                }
                neighbors_considered_from_adj++;
                if (neighbors_considered_from_adj >= max_spatial_neighbors_to_consider) break; // Limit the number of spatial neighbors added
            }
        }

        // If the current pool of customers to explore is exhausted, but we still need more customers,
        // pick a new random seed customer from the unselected ones to ensure we reach the target size.
        if (pool_idx == customerPool.size() && selectedCustomers.size() < numCustomersToRemove) {
            int new_seed_attempts = 0;
            const int max_new_seed_attempts = 100; // Prevent infinite loops in rare cases
            while (selectedCustomers.size() < numCustomersToRemove && new_seed_attempts < max_new_seed_attempts) {
                int new_seed = getRandomNumber(1, instance.numCustomers);
                if (selectedCustomers.find(new_seed) == selectedCustomers.end()) {
                    selectedCustomers.insert(new_seed);
                    customerPool.push_back(new_seed);
                    break; // Found a new seed, continue expansion
                }
                new_seed_attempts++;
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Heuristic for Step 3: Ordering of the removed customers
// Goal: Order the removed customers for greedy reinsertion.
// This heuristic prioritizes customers based on "difficulty" (tight time windows, distance from depot)
// and then introduces a small amount of stochastic perturbation.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Structure to hold customer data needed for sorting
    struct CustomerSortData {
        int id;
        float tw_width;
        float dist_from_depot;
    };

    std::vector<CustomerSortData> sort_data;
    sort_data.reserve(customers.size());

    // Populate sort_data for each customer to be reinserted
    for (int customer_id : customers) {
        sort_data.push_back({customer_id, instance.TW_Width[customer_id], instance.distanceMatrix[0][customer_id]});
    }

    // Define the custom comparison logic for sorting:
    // 1. Primary sort key: Time Window Width.
    //    Customers with smaller (tighter) time window widths are considered "harder" to place,
    //    so they should come first. If TW_Width is 0, it means service must begin exactly
    //    at startTW, which is the tightest constraint, so assign a very high "difficulty" score.
    // 2. Secondary sort key (for tie-breaking): Distance from Depot.
    //    If time window widths are equal, customers further from the depot are considered
    //    "harder" to place, so they should come first.
    std::sort(sort_data.begin(), sort_data.end(), [](const CustomerSortData& a, const CustomerSortData& b) {
        // Handle zero TW_Width: If width is 0, it represents the tightest constraint.
        // Assign a large value to its reciprocal to ensure it is prioritized.
        // Otherwise, use 1.0f / TW_Width (smaller width -> larger reciprocal).
        float a_tw_difficulty_score = (a.tw_width == 0.0f) ? 1e9f : (1.0f / a.tw_width);
        float b_tw_difficulty_score = (b.tw_width == 0.0f) ? 1e9f : (1.0f / b.tw_width);

        if (a_tw_difficulty_score != b_tw_difficulty_score) {
            return a_tw_difficulty_score > b_tw_difficulty_score; // Higher difficulty score (tighter TW) first
        }
        // If TW difficulty scores are equal, sort by distance from depot (larger distance first)
        return a.dist_from_depot > b.dist_from_depot;
    });

    // Copy the sorted customer IDs back to the original 'customers' vector
    for (size_t i = 0; i < sort_data.size(); ++i) {
        customers[i] = sort_data[i].id;
    }

    // Introduce stochastic perturbation to the sorted order:
    // Iterate through the sorted list and with a small probability, swap adjacent elements.
    // This adds diversity to the reinsertion process across iterations.
    const float swap_probability = 0.05f; // 5% chance to swap adjacent elements
    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFractionFast() < swap_probability) {
            std::swap(customers[i], customers[i + 1]);
        }
    }
}