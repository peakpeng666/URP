#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // Required for std::sort, std::min, std::swap
#include <vector>    // Required for std::vector
#include <utility>   // Required for std::pair

// Customer selection heuristic for the Large Neighborhood Search (LNS) framework.
// This function selects a subset of customers to be removed from the current solution.
// The selection aims to be stochastic, fast, and to ensure selected customers are
// geographically close to at least one or a few other selected customers.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_list; 

    int num_customers = sol.instance.numCustomers;
    // Determine the number of customers to remove stochastically.
    // For 500 customers, this range results in 10 to 25 customers removed.
    int num_to_remove = getRandomNumber(num_customers / 50, num_customers / 20);

    if (num_to_remove <= 0 || num_customers == 0) {
        return {};
    }

    // 1. Start with a random customer to seed the removal 'cluster'.
    int initial_customer = getRandomNumber(1, num_customers);
    selected_set.insert(initial_customer);
    selected_list.push_back(initial_customer);

    // This vector acts as a dynamic pool of customers from which we can expand the selection.
    // It contains customers already selected that might have unselected neighbors.
    std::vector<int> expansion_pool;
    expansion_pool.push_back(initial_customer);

    // Limit the number of closest neighbors to consider for expansion.
    // This keeps the process fast and focuses on local connectivity.
    int max_neighbors_to_consider = 10; 

    while (selected_set.size() < num_to_remove) {
        if (expansion_pool.empty()) {
            // Fallback: If the current expansion pool is exhausted (meaning all relevant neighbors
            // of the already selected customers have also been selected), pick a new random
            // unselected customer to continue growing the set from a different point.
            int new_seed_customer = -1;
            int attempts = 0;
            // Iterate a few times to find an unselected customer.
            while (new_seed_customer == -1 && attempts < num_customers * 2 && selected_set.size() < num_customers) {
                 int rand_cust = getRandomNumber(1, num_customers);
                 if (selected_set.find(rand_cust) == selected_set.end()) {
                     new_seed_customer = rand_cust;
                     break;
                 }
                 attempts++;
            }
            if (new_seed_customer == -1) { 
                 break; // Cannot select more customers (e.g., all customers are already selected)
            }
            selected_set.insert(new_seed_customer);
            selected_list.push_back(new_seed_customer);
            expansion_pool.push_back(new_seed_customer);
            // Check immediately if target size is met after adding a new seed.
            if (selected_set.size() == num_to_remove) {
                break;
            }
        }

        // 2. Stochastically pick a customer from the current expansion pool to expand from.
        int pool_idx = getRandomNumber(0, (int)expansion_pool.size() - 1);
        int current_customer_for_expansion = expansion_pool[pool_idx];

        const auto& neighbors = sol.instance.adj[current_customer_for_expansion];
        bool neighbor_added_in_current_iteration = false;

        if (!neighbors.empty()) {
            // 3. Stochastically pick a neighbor from the closest ones (up to max_neighbors_to_consider).
            int actual_neighbors_to_consider = std::min((int)neighbors.size(), max_neighbors_to_consider);
            
            // Create a temporary vector of indices to shuffle, to ensure non-biased random selection among top N.
            std::vector<int> neighbor_indices(actual_neighbors_to_consider);
            for (int i = 0; i < actual_neighbors_to_consider; ++i) {
                neighbor_indices[i] = i;
            }
            
            // Perform a fast partial shuffle (Fisher-Yates).
            for (int i = actual_neighbors_to_consider - 1; i > 0; --i) {
                int j = getRandomNumber(0, i);
                std::swap(neighbor_indices[i], neighbor_indices[j]);
            }

            for (int idx : neighbor_indices) {
                int neighbor_id = neighbors[idx];
                if (selected_set.find(neighbor_id) == selected_set.end()) { // If the neighbor is not already selected
                    selected_set.insert(neighbor_id);
                    selected_list.push_back(neighbor_id);
                    expansion_pool.push_back(neighbor_id); // Add newly selected customer to the pool for further expansion
                    neighbor_added_in_current_iteration = true;
                    break; // Only add one neighbor per expansion step to control growth and ensure diversity.
                }
            }
        }

        // If no new neighbor was added from 'current_customer_for_expansion' in this step,
        // remove it from the expansion pool to avoid re-selecting it uselessly in future iterations.
        if (!neighbor_added_in_current_iteration) {
            // O(1) removal by swapping with last element and popping.
            std::swap(expansion_pool[pool_idx], expansion_pool.back());
            expansion_pool.pop_back();
        }
    }
    return selected_list;
}


// Function selecting the order in which to reinsert the customers.
// This heuristic sorts customers primarily by their distance from the depot,
// incorporating stochastic noise to ensure diversity over many iterations.
// Reinserting customers farthest from the depot first can encourage more
// "meaningful changes" by forcing the reinsertion algorithm to address
// potentially harder-to-place customers early.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Calculate a representative average distance to the depot for scaling the stochastic noise.
    float avg_dist_to_depot = 0.0f;
    if (instance.numCustomers > 0) {
        for (int i = 1; i <= instance.numCustomers; ++i) { // Iterates through customer IDs (1 to numCustomers)
            avg_dist_to_depot += instance.distanceMatrix[0][i]; // Distance from depot (node 0)
        }
        avg_dist_to_depot /= instance.numCustomers;
    }
    
    // Define the magnitude of stochastic noise. This ensures the noise is proportional
    // to the typical distances in the problem instance, making it relevant but not dominant.
    float noise_magnitude = avg_dist_to_depot * 0.1f; // e.g., 10% of average distance

    // Create pairs of (score, customer_id) for sorting.
    // The score combines the customer's distance from the depot with added stochastic noise.
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float dist_to_depot = instance.distanceMatrix[0][customer_id];
        // Generate noise in the range [-noise_magnitude/2, +noise_magnitude/2].
        // getRandomFractionFast() returns a float in [0, 1].
        float noise = (getRandomFractionFast() - 0.5f) * noise_magnitude;
        float score = dist_to_depot + noise;
        customer_scores.emplace_back(score, customer_id);
    }

    // Sort customers based on their calculated score in descending order.
    // Customers farther from the depot (higher score) will appear earlier in the list.
    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort by score in descending order
    });

    // Update the original 'customers' vector with the newly determined sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}