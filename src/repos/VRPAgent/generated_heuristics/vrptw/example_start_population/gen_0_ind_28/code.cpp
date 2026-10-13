#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::shuffle, std::min_element, std::swap
#include <limits>    // For std::numeric_limits
#include <numeric>   // For std::iota

// Assuming Solution, Instance, Tour, Utils.h are available
// These structs and their members (e.g., `sol.instance.numCustomers`, `instance.distanceMatrix`, `instance.adj`)
// are implicitly accessible given the problem setup and provided header information.

// Helper function to get a random element from a vector and remove it efficiently.
// This prevents repeated re-shuffling or costly removals from the middle of the vector.
template <typename T>
T pop_random_element(std::vector<T>& vec) {
    if (vec.empty()) {
        // This case should ideally not be hit if logic correctly manages vector state.
        // For robustness, returning a default constructed T or throwing an error is an option.
        // Given problem context, an empty vector implies no elements to pick from.
        return T(); 
    }
    int idx = getRandomNumber(0, vec.size() - 1);
    T element = vec[idx];
    // Swap the element to be removed with the last element and then pop_back().
    // This is an O(1) operation, making it very fast for large vectors.
    vec[idx] = vec.back(); 
    vec.pop_back();        
    return element;
}

// Heuristic for Step 1: Customer Selection
// Selects a subset of customers to remove based on proximity and stochastic expansion.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> candidates_for_expansion; // Customers from which to expand the selection

    // Determine the number of customers to remove.
    // This range (e.g., 2% to 6% of total customers, with a minimum of 10)
    // allows for varying degrees of perturbation and scales with instance size.
    int num_to_remove = std::max(10, (int)(sol.instance.numCustomers * (0.02 + getRandomFractionFast() * 0.04)));
    num_to_remove = std::min(num_to_remove, sol.instance.numCustomers); // Ensure not to remove more than available

    // Handle very small instances to prevent issues if num_to_remove calculation yields too high a value.
    if (sol.instance.numCustomers <= 20) { // Arbitrary small threshold
        num_to_remove = std::min(sol.instance.numCustomers, getRandomNumber(5, 10));
    }


    // 1. Seed Selection: Start with a randomly chosen customer.
    // Customer IDs are typically 1 to numCustomers, node 0 is the depot.
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_seed);
    candidates_for_expansion.push_back(initial_seed);

    float prob_add_neighbor = 0.65; // Probability to add a close neighbor to the selection set.

    // 2. Expansion Loop: Iteratively add customers based on proximity to selected ones.
    while (selected_customers_set.size() < num_to_remove) {
        if (candidates_for_expansion.empty()) {
            // If all current candidates for expansion are exhausted, pick a new random
            // unselected customer as a new seed to continue reaching 'num_to_remove'.
            // This ensures we always make progress and can start new, disconnected "chains".
            std::vector<int> unselected_customers_pool;
            for(int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selected_customers_set.find(i) == selected_customers_set.end()) {
                    unselected_customers_pool.push_back(i);
                }
            }
            if (unselected_customers_pool.empty()) { // No more customers to select
                break;
            }
            int new_seed = pop_random_element(unselected_customers_pool);
            
            selected_customers_set.insert(new_seed);
            candidates_for_expansion.push_back(new_seed);
            if (selected_customers_set.size() >= num_to_remove) {
                break; // Reached target size after adding new seed
            }
        }
        
        // Pick a random customer from the candidates list to expand from.
        int current_customer = pop_random_element(candidates_for_expansion);

        // Limit the number of neighbors to consider from the precomputed adjacency list (`adj`)
        // to keep the selection process fast and focused on local proximity.
        int num_neighbors_to_check = std::min((int)sol.instance.adj[current_customer].size(), getRandomNumber(5, 15)); 
        
        // Iterate over a subset of the closest neighbors (from `adj` which is sorted by distance).
        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor_node_id = sol.instance.adj[current_customer][i];

            // Ensure the neighbor is a customer (not the depot, node 0) and not already selected.
            if (neighbor_node_id == 0 || selected_customers_set.count(neighbor_node_id)) {
                continue;
            }

            // Probabilistically add the neighbor to introduce stochasticity.
            if (getRandomFractionFast() < prob_add_neighbor) {
                selected_customers_set.insert(neighbor_node_id);
                candidates_for_expansion.push_back(neighbor_node_id);
                if (selected_customers_set.size() >= num_to_remove) {
                    goto end_selection_loop; // Efficiently exit nested loops when target size is reached.
                }
            }
        }
    }

end_selection_loop:; // Label for the goto statement.

    // Convert the set of selected customers to a vector for return.
    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

// Heuristic for Step 3: Ordering of Removed Customers
// Sorts the removed customers based on a Nearest Neighbor Chain approach with stochasticity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<int> remaining_customers = customers;
    std::vector<int> sorted_customers;
    sorted_customers.reserve(customers.size()); // Pre-allocate memory for efficiency

    // 1. Pick a random starting customer for the chain.
    int start_idx = getRandomNumber(0, remaining_customers.size() - 1);
    int current_customer = remaining_customers[start_idx];
    
    sorted_customers.push_back(current_customer);
    // Efficiently remove the selected starting customer from the remaining list.
    std::swap(remaining_customers[start_idx], remaining_customers.back());
    remaining_customers.pop_back();

    // Probability to sometimes pick a random customer instead of the closest.
    // This adds stochasticity and helps explore diverse reinsertion orders.
    float stochastic_diversion_prob = 0.15; 

    // 2. Build the Nearest Neighbor Chain.
    while (!remaining_customers.empty()) {
        int next_customer_idx = -1;

        if (getRandomFractionFast() < stochastic_diversion_prob) {
            // Stochastic diversion: Instead of finding the closest, pick a random remaining customer.
            next_customer_idx = getRandomNumber(0, remaining_customers.size() - 1);
        } else {
            // Find the closest customer to the current_customer among the remaining ones.
            float min_dist = std::numeric_limits<float>::max(); // Initialize with max possible float value
            for (int i = 0; i < remaining_customers.size(); ++i) {
                int candidate = remaining_customers[i];
                float dist = instance.distanceMatrix[current_customer][candidate];
                if (dist < min_dist) {
                    min_dist = dist;
                    next_customer_idx = i;
                }
            }
        }
        
        current_customer = remaining_customers[next_customer_idx];
        sorted_customers.push_back(current_customer);
        // Efficiently remove the chosen customer from the remaining list.
        std::swap(remaining_customers[next_customer_idx], remaining_customers.back());
        remaining_customers.pop_back();
    }

    // Update the original `customers` vector with the new sorted order.
    customers = sorted_customers;
}