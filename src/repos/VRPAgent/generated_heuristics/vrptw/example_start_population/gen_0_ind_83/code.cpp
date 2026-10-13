#include "AgentDesigned.h" // Includes Solution, Instance, Tour definitions
#include <vector>
#include <random>
#include <algorithm> // For std::shuffle, std::sort
#include <unordered_set> // For efficient tracking of selected customers
#include <utility> // For std::pair

// Assuming Utils.h provides getRandomNumber
#include "Utils.h"

// Step 1: Customer selection heuristic
// This heuristic selects a subset of customers to remove.
// It aims to select customers that are "connected" or spatially close,
// while incorporating stochasticity to ensure diversity over many iterations.
std::vector<int> select_by_llm_1(const Solution& sol) {
    static thread_local std::mt19937 gen(std::random_device{}());

    std::unordered_set<int> selectedCustomers;
    std::vector<int> frontier; // Used for a BFS-like expansion from selected customers

    // Determine the number of customers to remove.
    // A dynamic range provides more exploration than a fixed number.
    int numCustomersToRemove = getRandomNumber(15, 30); 

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }
    // Cap the number of customers to remove at the total number of customers
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // 1. Pick an initial seed customer to start the selection process.
    // This customer is chosen randomly.
    int seed_customer_id;
    // Loop to ensure the selected seed is not somehow already in selectedCustomers
    // (e.g., if this function was called in a weird state or numCustomersToRemove is close to totalCustomers)
    do {
        seed_customer_id = getRandomNumber(1, sol.instance.numCustomers); // Customer IDs are 1-indexed
    } while (selectedCustomers.count(seed_customer_id) > 0);

    selectedCustomers.insert(seed_customer_id);
    frontier.push_back(seed_customer_id);

    int current_frontier_idx = 0; // Pointer to simulate a queue for frontier expansion

    // 2. Expand the selection by adding neighbors of already selected customers.
    // This process continues until the desired number of customers is reached.
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (current_frontier_idx >= frontier.size()) {
            // The current "cluster" of selected customers has no more unselected neighbors.
            // To continue reaching `numCustomersToRemove`, pick a new random seed from the remaining unselected customers.
            int new_seed_id;
            bool found_new_seed = false;
            // Iterate and pick a new seed until an unselected one is found.
            // Limit attempts to avoid infinite loop in edge cases.
            for (int attempt = 0; attempt < sol.instance.numCustomers * 2; ++attempt) { 
                new_seed_id = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.count(new_seed_id) == 0) {
                    selectedCustomers.insert(new_seed_id);
                    frontier.push_back(new_seed_id);
                    found_new_seed = true;
                    break;
                }
            }
            if (!found_new_seed) { 
                // No more unselected customers could be found. This happens if all are selected
                // or if `numCustomersToRemove` was set too high for available unselected customers.
                break; 
            }
        }
        
        int current_customer = frontier[current_frontier_idx++]; // Get customer from frontier to process
        
        // Collect potential new neighbors from the current customer's vicinity.
        std::vector<int> potential_neighbors;
        // `instance.adj` provides neighbors sorted by distance, which is efficient.
        for (int neighbor_id : sol.instance.adj[current_customer]) {
            if (selectedCustomers.count(neighbor_id) == 0) { // Check if neighbor is not already selected
                potential_neighbors.push_back(neighbor_id);
            }
        }
        
        // Stochastically add a few neighbors from the potential list.
        // Shuffling ensures randomness in which neighbors are picked, even if `adj` is sorted.
        std::shuffle(potential_neighbors.begin(), potential_neighbors.end(), gen); 
        
        // Add between 1 and 3 neighbors from the shuffled list, up to what's available and needed.
        int num_to_add_from_neighbors = getRandomNumber(1, std::min((int)potential_neighbors.size(), 3)); 
        
        for (int i = 0; i < num_to_add_from_neighbors && selectedCustomers.size() < numCustomersToRemove; ++i) {
            // .second of insert returns true if the insertion successfully occurred (i.e., element was new)
            if (selectedCustomers.insert(potential_neighbors[i]).second) { 
                frontier.push_back(potential_neighbors[i]); // Add newly selected neighbor to frontier for future expansion
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Step 3: Ordering of the removed customers
// This heuristic sorts the removed customers, influencing the greedy reinsertion process.
// It prioritizes "harder" customers for earlier reinsertion while maintaining stochasticity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());

    if (customers.empty()) {
        return;
    }

    // Store pairs of (score, customer_id) to sort them.
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        // Calculate a "difficulty" score for each customer.
        // Higher score indicates a harder-to-place customer, thus prioritized for earlier reinsertion.
        float score = 0.0f;
        
        // 1. Contribution from time window width: Tighter windows (smaller width) are generally harder to fit.
        // Using inverse of TW_Width gives higher scores for tighter windows.
        // Adding a small epsilon to avoid division by zero if TW_Width could be 0.
        score += (1.0f / (instance.TW_Width[customer_id] + 1e-6f)); 

        // 2. Contribution from demand: Higher demand customers are harder to fit into vehicle capacity.
        score += static_cast<float>(instance.demand[customer_id]) * 0.5f; // Weighted by 0.5

        // 3. Contribution from service time: Longer service times reduce route flexibility.
        score += instance.serviceTime[customer_id] * 0.2f; // Weighted by 0.2

        scored_customers.push_back({score, customer_id});
    }

    // Sort customers in descending order of their calculated scores (hardest customers first).
    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Introduce stochasticity: Perform a controlled number of random swaps on the sorted list.
    // This perturbs the perfect sorted order slightly, ensuring diversity in reinsertion attempts
    // over millions of iterations, while generally keeping harder customers near the front.
    int num_swaps = static_cast<int>(customers.size() * 0.2); // Swap roughly 20% of the customers' positions
    
    // Ensure at least one swap for lists with more than one customer, if num_swaps calculates to 0.
    if (num_swaps < 1 && customers.size() > 1) { 
        num_swaps = 1;
    }
    // No swaps needed for 0 or 1 customer.
    if (customers.size() <= 1) { 
        num_swaps = 0;
    }

    std::uniform_int_distribution<> distrib(0, customers.size() - 1);

    for (int i = 0; i < num_swaps; ++i) {
        int idx1 = distrib(gen);
        int idx2 = distrib(gen);
        if (idx1 != idx2) { // Only swap if indices are different
            std::swap(scored_customers[idx1], scored_customers[idx2]);
        }
    }

    // Update the original 'customers' vector with the new, stochastically ordered sequence.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}