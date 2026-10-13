#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair

#include "Utils.h"

// For std::shuffle, we need a random number generator.
// Use thread_local to ensure each thread has its own generator and for performance.
static thread_local std::mt19937 g_rng(std::random_device{}());

// Customer selection heuristic for the LNS framework.
// Selects a subset of customers to remove based on a neighborhood expansion strategy.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    
    // Determine the number of customers to remove in this iteration.
    // A small range (8 to 25) ensures focused perturbations while providing diversity.
    int numCustomersToRemove = getRandomNumber(8, 25); 

    const Instance& instance = sol.instance;

    // The heuristic aims to select customers that are spatially "close" to each other
    // to encourage meaningful localized changes during reinsertion. This is achieved
    // by growing "neighborhoods" or "clusters" around randomly chosen seed customers.
    // Multiple disconnected clusters are allowed if a single expansion doesn't yield
    // the desired number of customers.

    while (selectedCustomers.size() < numCustomersToRemove) {
        // Step 1: Select a seed customer for the current cluster.
        // A random customer ID (1-indexed, from 1 to instance.numCustomers) is chosen.
        // This allows for selection of customers currently served or unserved,
        // making the reinsertion phase potentially capable of inserting new customers.
        int seed_customer_id = getRandomNumber(1, instance.numCustomers);
        
        // Add the seed customer to the set of selected customers if it hasn't been selected yet.
        if (selectedCustomers.find(seed_customer_id) == selectedCustomers.end()) {
            selectedCustomers.insert(seed_customer_id);
            if (selectedCustomers.size() == numCustomersToRemove) {
                break; // Target number of customers reached
            }
        }

        // Use a vector as a queue for a BFS-like expansion within the current cluster.
        std::vector<int> expansion_queue;
        expansion_queue.push_back(seed_customer_id);
        size_t head = 0; // Pointer to the current customer being expanded from in the queue

        // Step 2: Expand the cluster from the seed.
        // Continue expanding as long as there are customers in the queue to process
        // and the target number of customers to remove has not been met.
        while (head < expansion_queue.size() && selectedCustomers.size() < numCustomersToRemove) {
            int current_customer_id = expansion_queue[head];
            head++; // Move to the next customer in the queue

            // Retrieve the neighbors of the current customer from instance.adj.
            // Assumes instance.adj is indexed by node ID (where node 0 is the depot,
            // and node `customer_id` corresponds to `customer_id`).
            const std::vector<int>& neighbors = instance.adj[current_customer_id]; 
            
            // To ensure efficiency and add stochasticity, only a subset of the closest
            // neighbors (pre-sorted in `instance.adj`) are considered. This subset
            // is then shuffled to vary the order in which neighbors are evaluated.
            int num_neighbors_to_sample = std::min((int)neighbors.size(), getRandomNumber(5, 15)); 

            std::vector<int> sampled_neighbors;
            sampled_neighbors.reserve(num_neighbors_to_sample);
            for(int i = 0; i < num_neighbors_to_sample; ++i) {
                sampled_neighbors.push_back(neighbors[i]);
            }
            std::shuffle(sampled_neighbors.begin(), sampled_neighbors.end(), g_rng); // Use the thread-local RNG

            // Iterate through the sampled and shuffled neighbors.
            for (int neighbor_id : sampled_neighbors) {
                if (selectedCustomers.size() >= numCustomersToRemove) {
                    break; // Target number of customers reached
                }

                // Ensure the neighbor_id is a valid customer ID (1 to instance.numCustomers).
                // This check is important if `instance.adj` might contain the depot (node 0)
                // or other non-customer nodes.
                if (neighbor_id >= 1 && neighbor_id <= instance.numCustomers) {
                    if (selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                        // Introduce stochasticity: add the neighbor to the selected set
                        // with a certain probability (e.g., 70%). This prevents clusters
                        // from always expanding in the same deterministic way.
                        if (getRandomFractionFast() < 0.7f) { 
                            selectedCustomers.insert(neighbor_id);
                            expansion_queue.push_back(neighbor_id); // Add to queue for further expansion
                        }
                    }
                }
            }
        }
    }
    
    // Convert the `unordered_set` of selected customer IDs into a `std::vector`
    // for the return type.
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Heuristic for ordering the removed customers before greedy reinsertion.
// This order can significantly influence the quality of the re-built solution.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Create a vector of pairs to associate each customer with a calculated score.
    // This allows sorting based on these scores while retaining the original customer IDs.
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Calculate a score for each customer.
    // The primary sorting criterion is the customer's prize, as maximizing total collected
    // prize is a direct objective of the PCVRP. Prioritizing high-prize customers
    // for early reinsertion aims to secure their inclusion in the solution.
    //
    // A small amount of stochastic noise is added to the prize. This perturbation
    // ensures that customers with identical or very similar prizes are ordered
    // differently across millions of iterations, fostering search diversity.
    // `getRandomFractionFast()` returns a float in [0, 1]. Multiplying it by a small
    // constant (0.1f) ensures the prize remains the dominant factor, while still
    // introducing sufficient random variation.
    for (int customer_id : customers) {
        // Access the prize for the given customer_id.
        // Assumes instance.prizes is indexed by node ID (where node `customer_id`
        // corresponds to `customer_id`).
        float prize = instance.prizes[customer_id]; 
        
        // Calculate the score: base prize + stochastic noise.
        float score = prize + getRandomFractionFast() * 0.1f; 
        scored_customers.push_back({score, customer_id});
    }

    // Sort the `scored_customers` in descending order based on their calculated score.
    // This places customers with higher prizes (and slight stochastic preference)
    // at the beginning of the list, meaning they will be considered first for reinsertion.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort in descending order of score
    });

    // Update the original `customers` vector with the new sorted order of customer IDs.
    // This vector is then used by the LNS framework for greedy reinsertion.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}