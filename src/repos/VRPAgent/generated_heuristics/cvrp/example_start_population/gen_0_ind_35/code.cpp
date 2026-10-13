#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::shuffle, std::sort
#include <deque> // For std::deque (if chosen, but vector for random access is better for this logic)
#include <utility> // For std::pair, std::swap
#include <cmath> // For std::min

// Assuming Utils.h provides these functions
// int getRandomNumber(int min, int max);
// float getRandomFraction(float min = 0.0, float max = 1.0);
// float getRandomFractionFast(); // Fast random float in [0, 1]

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> candidatePool; // Customers whose neighbors are candidates for selection

    // Determine the number of customers to remove.
    // This value is stochastic and scales slightly with instance size,
    // but is capped to ensure a small number is removed per iteration.
    int max_customers_to_remove = std::min((int)(sol.instance.numCustomers * 0.05) + 1, 30); // Max 5% or 30, whichever is smaller.
    if (max_customers_to_remove < 15 && sol.instance.numCustomers >= 15) { // Ensure a minimum for large instances
        max_customers_to_remove = 15;
    }
    int numCustomersToRemove = getRandomNumber(15, max_customers_to_remove);
    
    // Handle edge cases for very small instances
    if (sol.instance.numCustomers == 0 || numCustomersToRemove == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // 1. Pick an initial seed customer randomly to start the removal cluster.
    int initial_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers_set.insert(initial_seed_customer);
    candidatePool.push_back(initial_seed_customer);

    // This loop expands the set of selected customers by adding neighbors of already selected ones,
    // thereby ensuring locality. Stochasticity is introduced through random choices within the process.
    while (selectedCustomers_set.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            // If the current candidate pool is exhausted (meaning the "cluster" we were growing is fully explored
            // or too small), pick a new, disconnected seed customer. This ensures we can always reach the target
            // number of removed customers and adds diversity to the selection pattern.
            int new_seed_customer = -1;
            // Attempt to find a new seed by random sampling first (faster for large `numCustomers`)
            for (int attempt = 0; attempt < 50; ++attempt) { // Max 50 attempts to find a random unselected customer
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers_set.find(potential_seed) == selectedCustomers_set.end()) {
                    new_seed_customer = potential_seed;
                    break;
                }
            }
            if (new_seed_customer == -1) { // Fallback: iterate through all customers if random attempts fail
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (selectedCustomers_set.find(i) == selectedCustomers_set.end()) {
                        new_seed_customer = i;
                        break;
                    }
                }
            }

            if (new_seed_customer == -1) { // Should only happen if all customers are already selected
                break;
            }

            selectedCustomers_set.insert(new_seed_customer);
            candidatePool.push_back(new_seed_customer);
        }

        // Randomly pick a customer from the candidatePool to expand from.
        // This customer acts as the "center" for further diffusion.
        int pool_idx = getRandomNumber(0, candidatePool.size() - 1);
        int current_customer_for_expansion = candidatePool[pool_idx];
        
        // Remove current_customer_for_expansion from candidatePool for efficient processing.
        // Swap with the last element and pop_back for O(1) average time complexity.
        std::swap(candidatePool[pool_idx], candidatePool.back());
        candidatePool.pop_back();

        // Determine how many nearest neighbors of the `current_customer_for_expansion` to consider.
        // This is also stochastic to vary the shape and density of the removed cluster.
        int num_neighbors_to_consider = getRandomNumber(3, 8); 

        // Get the pre-sorted list of neighbors by distance from the instance data.
        const auto& adj_list = sol.instance.adj[current_customer_for_expansion];
        
        // Take a subset of the nearest neighbors and shuffle them to add more stochasticity
        // regarding which exact neighbors are added next.
        std::vector<int> shuffled_neighbors;
        for(size_t i = 0; i < std::min((size_t)num_neighbors_to_consider, adj_list.size()); ++i) {
            shuffled_neighbors.push_back(adj_list[i]);
        }
        // Use a thread_local random number generator for std::shuffle to ensure good quality randomness
        // and avoid issues in multi-threaded environments.
        static thread_local std::mt19937 gen_shuffle(std::random_device{}()); 
        std::shuffle(shuffled_neighbors.begin(), shuffled_neighbors.end(), gen_shuffle);

        // Add the selected neighbors to the `selectedCustomers_set` and `candidatePool`.
        for (int neighbor_id : shuffled_neighbors) {
            if (selectedCustomers_set.size() == numCustomersToRemove) {
                break; // Reached target, stop adding.
            }
            // Ensure `neighbor_id` is a valid customer ID (1 to numCustomers) and not already selected.
            if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers && 
                selectedCustomers_set.find(neighbor_id) == selectedCustomers_set.end()) {
                selectedCustomers_set.insert(neighbor_id);
                candidatePool.push_back(neighbor_id);
            }
        }

        // Stochastic broadening: Occasionally, add a completely random customer that is not part of
        // the current diffusion process. This introduces greater diversity in the removed set
        // and helps escape local optima by breaking up existing clusters.
        if (getRandomFractionFast() < 0.1 && selectedCustomers_set.size() < numCustomersToRemove) { // ~10% chance
            int random_customer_for_diversity = -1;
            // Attempt to find a new random customer for diversity quickly.
            for(int attempt = 0; attempt < 5; ++attempt){ 
                int potential_div_customer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers_set.find(potential_div_customer) == selectedCustomers_set.end()) {
                    random_customer_for_diversity = potential_div_customer;
                    break;
                }
            }

            if(random_customer_for_diversity != -1) {
                selectedCustomers_set.insert(random_customer_for_diversity);
                candidatePool.push_back(random_customer_for_diversity); // Add it to the pool for potential expansion later.
            }
        }
    }

    // Convert the unordered_set to a vector for return.
    return std::vector<int>(selectedCustomers_set.begin(), selectedCustomers_set.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // Calculate a reinsertion score for each customer.
    // The primary factor is customer demand, as higher demand customers are more constrained
    // and their placement can significantly impact remaining capacity.
    // Stochastic noise is added to the demand score to introduce diversity in sorting order
    // over millions of iterations, even for customers with identical demands.
    for (int customer_id : customers) {
        float score = static_cast<float>(instance.demand[customer_id]); 
        
        // Add a small amount of random noise relative to the vehicle capacity.
        // This ensures that even customers with the same demand have slightly different
        // effective scores, breaking ties randomly and promoting diverse repair sequences.
        score += getRandomFractionFast() * 0.05 * instance.vehicleCapacity; // Noise up to 5% of vehicle capacity
        
        customer_scores.push_back({score, customer_id});
    }

    // Randomly decide whether to sort customers in descending or ascending order of their scores.
    // This provides two distinct strategies for reinsertion (e.g., high-demand first vs. low-demand first),
    // which can lead to different solution outcomes.
    bool sort_descending = (getRandomFractionFast() < 0.5);

    if (sort_descending) {
        // Sort by score in descending order (e.g., higher demand customers first).
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first > b.first; 
        });
    } else {
        // Sort by score in ascending order (e.g., lower demand customers first).
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first < b.first; 
        });
    }

    // Update the original `customers` vector with the newly determined order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}