#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::min
#include <vector>
#include <cmath>     // For std::pow
#include <utility>   // For std::pair

// Ensure getRandomNumber, getRandomFractionFast, and other utilities are available
// These are assumed to be defined in Utils.h and linked.

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatePool; // Customers from which to expand the selection

    // Determine the number of customers to remove, with stochasticity
    int numCustomersToRemove = getRandomNumber(15, 25); 

    // Step 1: Select an initial seed customer randomly
    // Customers are 1-indexed, so getRandomNumber(1, numCustomers) is correct.
    int initial_seed_c = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initial_seed_c);
    candidatePool.push_back(initial_seed_c);

    // Step 2: Iteratively expand the selection
    while (selectedCustomers.size() < numCustomersToRemove) {
        // Fallback: If candidatePool becomes empty (e.g., all neighbors of existing candidates are already selected)
        // or if it started empty (shouldn't happen with initial seed), add a new random seed.
        if (candidatePool.empty()) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            // Ensure the new seed is not already selected
            int retry_count = 0;
            const int max_retries = 100; // Prevent infinite loop on very small instances
            while (selectedCustomers.count(new_seed) && retry_count < max_retries) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                retry_count++;
            }
            // If still cannot find a new unselected customer after retries, just break
            if (selectedCustomers.count(new_seed)) {
                 break;
            }
            selectedCustomers.insert(new_seed);
            candidatePool.push_back(new_seed);
            if (selectedCustomers.size() >= numCustomersToRemove) {
                break; // Stop if target reached with the new seed
            }
            continue; // Continue to process the new seed
        }

        // Randomly pick a customer from the candidate pool to expand from
        int rand_idx_in_pool = getRandomNumber(0, (int)candidatePool.size() - 1);
        int current_c = candidatePool[rand_idx_in_pool];

        bool found_new_customer = false;
        // Try to find an unselected neighbor from current_c's adjacency list (which is sorted by distance)
        // We try a few times to increase the chance of finding a suitable neighbor.
        for (int attempt = 0; attempt < 5; ++attempt) {
            if (sol.instance.adj[current_c].empty()) {
                break; // No neighbors for this customer
            }

            // Probabilistically pick a neighbor index, biasing towards closer ones (smaller indices)
            // pow(getRandomFractionFast(), X) where X > 1 heavily biases towards values closer to 0.
            // This means smaller indices in adj (closer neighbors) are much more likely to be chosen.
            double random_val = getRandomFractionFast(); // Generates a float in [0, 1]
            int neighbor_idx_in_adj = static_cast<int>(std::pow(random_val, 4.0) * sol.instance.adj[current_c].size());
            
            // Ensure the calculated index is within bounds
            neighbor_idx_in_adj = std::min(neighbor_idx_in_adj, (int)sol.instance.adj[current_c].size() - 1);
            
            int potential_new_c = sol.instance.adj[current_c][neighbor_idx_in_adj];

            // If the potential new customer is not already selected
            if (selectedCustomers.find(potential_new_c) == selectedCustomers.end()) {
                selectedCustomers.insert(potential_new_c);
                candidatePool.push_back(potential_new_c);
                found_new_customer = true;
                break; // Found a new customer, break from attempts for current_c
            }
        }

        // If no new customer was found from current_c after attempts, remove current_c from candidatePool.
        // This prevents repeatedly trying to expand from an "exhausted" node.
        if (!found_new_customer) {
            // Remove the current customer from the candidate pool to avoid re-selecting it if it can't find new neighbors
            candidatePool.erase(candidatePool.begin() + rand_idx_in_pool);
        }
    }

    // Convert the unordered_set to a vector for return
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // We want to prioritize reinsertion of customers that are "more valuable" or "easier to fit".
    // A heuristic combining prize, demand, and proximity to depot seems reasonable.
    // Higher score means higher priority for reinsertion.
    
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size()); // Pre-allocate memory

    // Calculate a score for each customer
    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float demand = instance.demand[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id]; // Distance from depot (node 0)

        // Combine factors into a score:
        // - High prize is highly desirable.
        // - Low demand is easier to fit (inverse relationship).
        // - Closer to depot is potentially easier to route (inverse relationship).
        // - Add a small random component for stochasticity and tie-breaking.
        
        float score = prize * 1000.0f; // High weight for prize
        
        // Penalize demand. Use a small constant to avoid division by zero or large numbers for very small demands.
        score -= demand * 5.0f; // Moderate penalty for demand

        // Penalize distance to depot. Use a small constant to avoid division by zero.
        score -= dist_to_depot * 0.1f; // Light penalty for distance

        // Add stochastic noise for diversity across iterations
        score += getRandomFractionFast() * 1.0f; // Small random perturbation

        customer_scores.push_back({score, customer_id});
    }

    // Sort customers based on their calculated scores in descending order
    // (highest score first)
    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the input 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}