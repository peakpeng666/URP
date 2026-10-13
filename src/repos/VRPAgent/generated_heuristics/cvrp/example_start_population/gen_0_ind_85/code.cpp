#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort, std::shuffle, std::min
#include <utility>   // For std::pair
#include "Utils.h"

// Customer selection heuristic for LNS step 1.
// Selects a subset of customers to remove based on geographical proximity,
// forming one or more local clusters, with integrated stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> queue; // Used for BFS-like expansion of the cluster(s)

    // Determine the number of customers to remove.
    // This range (e.g., 2% to 5% of 500 customers) provides sufficient change
    // while keeping the removed set small for efficient reinsertion.
    int num_to_remove = getRandomNumber(10, 25);

    // Pick an initial random customer to start the removal cluster.
    int initial_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    
    selected_customers_set.insert(initial_customer_idx);
    queue.push_back(initial_customer_idx);

    size_t head = 0; // Pointer for the BFS queue, indicating current processing node

    // Loop until the desired number of customers are selected.
    while (selected_customers_set.size() < num_to_remove) {
        // If the current cluster's explorable neighbors are exhausted (queue is empty),
        // pick a new random customer not yet selected to start a new disconnected cluster.
        // This ensures the target number of removals is always met and adds diversity.
        if (head >= queue.size()) {
            int new_seed_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
            while (selected_customers_set.count(new_seed_customer_idx)) { // Ensure new seed is not already selected
                new_seed_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
            }
            selected_customers_set.insert(new_seed_customer_idx);
            queue.push_back(new_seed_customer_idx);
            
            if (selected_customers_set.size() == num_to_remove) {
                break; // Target reached
            }
        }

        int current_customer = queue[head++]; // Get the next customer to explore from the queue

        // Explore neighbors of the current customer.
        // The `adj` list provides neighbors sorted by distance, so checking the first few
        // ensures we prioritize geographically close customers.
        size_t num_neighbors_to_consider = std::min((size_t)sol.instance.adj[current_customer].size(), (size_t)5); // Consider top 5 closest neighbors

        for (size_t i = 0; i < num_neighbors_to_consider; ++i) {
            int neighbor_idx = sol.instance.adj[current_customer][i];

            // Ensure the neighbor is a customer (ID > 0) and has not already been selected.
            if (neighbor_idx > 0 && selected_customers_set.find(neighbor_idx) == selected_customers_set.end()) {
                // Incorporate stochasticity: add the neighbor to the set with a certain probability.
                // This prevents deterministic cluster shapes and promotes exploration.
                if (getRandomFractionFast() < 0.85f) { // 85% chance to add a valid neighbor
                    selected_customers_set.insert(neighbor_idx);
                    queue.push_back(neighbor_idx);
                    if (selected_customers_set.size() == num_to_remove) {
                        break; // Target reached
                    }
                }
            }
        }
    }

    // Convert the unordered_set of selected customers to a vector for return.
    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}


// Reinsertion ordering heuristic for LNS step 3.
// Sorts the removed customers based on their proximity to the depot,
// with a stochastic perturbation to ensure diversity over iterations.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customers_with_sort_key;
    customers_with_sort_key.reserve(customers.size()); // Pre-allocate memory

    // Define a perturbation range for stochasticity.
    // A perturbation_range of 0.3f means the distance can be scaled by (1.0 +/- 0.15),
    // introducing a +/- 15% variation around the true distance.
    const float perturbation_range = 0.3f; 

    for (int customer_id : customers) {
        // Get the actual distance from the depot (node 0) to the customer.
        float distance_to_depot = instance.distanceMatrix[0][customer_id];
        
        // Apply a stochastic noise to the distance.
        // (getRandomFractionFast() - 0.5f) maps [0,1] to [-0.5, 0.5], centering the noise around 0.
        float perturbed_distance = distance_to_depot * (1.0f + (getRandomFractionFast() - 0.5f) * perturbation_range);
        
        customers_with_sort_key.push_back({perturbed_distance, customer_id});
    }

    // Sort customers based on their perturbed distance to the depot in ascending order.
    // This heuristic prioritizes reinserting customers that are "closer" to the depot
    // (or its vicinity) first, which can help in re-establishing central routes efficiently.
    std::sort(customers_with_sort_key.begin(), customers_with_sort_key.end());

    // Update the original `customers` vector with the newly sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customers_with_sort_key[i].second;
    }
}