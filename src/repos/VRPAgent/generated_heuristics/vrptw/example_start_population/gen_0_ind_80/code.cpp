#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::min
#include "Utils.h"   // For getRandomNumber, getRandomFraction, getRandomFractionFast, argsort

// Heuristic for Step 1: Customer Selection
// Selects a subset of customers to remove from the current solution.
// The goal is to select customers that are somewhat geographically clustered
// to encourage meaningful reinsertion, while also incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList; // Stores selected customers in order of selection

    // Determine the number of customers to remove dynamically, within a small range.
    // This adds stochasticity to the size of the removed set.
    int min_remove = 15; // Minimum number of customers to remove
    int max_remove = 25; // Maximum number of customers to remove
    int numCustomersToRemove = getRandomNumber(min_remove, max_remove);

    // If numCustomersToRemove is 0 or less, return an empty list immediately.
    if (numCustomersToRemove <= 0) {
        return {};
    }

    // 1. Initial Seed Selection: Pick a random customer to start the "cluster".
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_seed);
    selectedCustomersList.push_back(initial_seed);

    // Parameters for controlling the expansion process.
    // max_consecutive_failed_expansions: If we repeatedly fail to find new neighbors,
    // it implies the current 'cluster' is exhausted or too small.
    int max_consecutive_failed_expansions = 5;
    int consecutive_failed_expansions = 0;

    // Loop until the desired number of customers are selected.
    while (selectedCustomersList.size() < numCustomersToRemove) {
        bool added_customer_in_iteration = false;
        
        // Try to expand from existing selected customers to maintain locality.
        // Pick a random customer from the already selected ones as a base for expansion.
        int base_customer_idx = getRandomNumber(0, selectedCustomersList.size() - 1);
        int base_customer = selectedCustomersList[base_customer_idx];

        // Iterate through the nearest neighbors of the base customer.
        // The `adj` list contains neighbors sorted by distance, which is ideal.
        // Limit the number of neighbors checked for performance and to keep clusters compact.
        int num_neighbors_to_check = std::min((int)sol.instance.adj[base_customer].size(), 10); 

        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor = sol.instance.adj[base_customer][i];

            // Skip depot (node 0) as it's not a customer to remove.
            if (neighbor == 0) continue; 

            // Add the neighbor probabilistically if it's not already selected.
            // This introduces stochasticity and allows for varied cluster shapes.
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() && getRandomFraction() < 0.7) { // 70% chance to add
                selectedCustomersSet.insert(neighbor);
                selectedCustomersList.push_back(neighbor);
                added_customer_in_iteration = true;
                consecutive_failed_expansions = 0; // Reset counter on success
                break; // Move to the next selection iteration if a customer was added
            }
        }

        // If no new customer was added from the current base_customer's neighbors.
        if (!added_customer_in_iteration) {
            consecutive_failed_expansions++;
        }

        // If expansion from the current cluster has repeatedly failed, or if no customers have been selected yet
        // (e.g., initial numCustomersToRemove was 0 and then increased somehow, though not typical for this setup),
        // pick a new random seed customer. This ensures diversity across iterations and guarantees
        // that `numCustomersToRemove` is eventually reached even if chosen clusters are small.
        if (consecutive_failed_expansions >= max_consecutive_failed_expansions || selectedCustomersList.empty()) {
            int new_seed;
            int safety_counter = 0;
            // Find a new random customer that has not been selected yet.
            do {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter++;
            } while (selectedCustomersSet.find(new_seed) != selectedCustomersSet.end() && safety_counter < sol.instance.numCustomers * 2); 
            // The safety_counter prevents infinite loops in highly unusual scenarios.

            // If a valid new seed is found (not already selected), add it.
            if (selectedCustomersSet.find(new_seed) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(new_seed);
                selectedCustomersList.push_back(new_seed);
                consecutive_failed_expansions = 0; // Reset consecutive failures as we have a new starting point.
            } else if (selectedCustomersList.empty() && safety_counter >= sol.instance.numCustomers * 2) {
                // Extreme fallback: if we couldn't even pick the first customer, add one to avoid infinite loop.
                if (numCustomersToRemove > 0) {
                     selectedCustomersList.push_back(getRandomNumber(1, sol.instance.numCustomers));
                }
                break;
            }
        }
    }
    return selectedCustomersList;
}

// Heuristic for Step 3: Ordering of Removed Customers
// Sorts the removed customers, defining the order in which they will be reinserted.
// Prioritizing customers that are "harder" to place can often lead to better solutions.
// Stochasticity is introduced to explore different reinsertion sequences.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<float> scores;
    scores.reserve(customers.size());

    // Calculate a 'priority' score for each customer.
    // Customers with tighter time windows (smaller TW_Width) are generally harder to place.
    // Adding a small random perturbation ensures stochastic behavior,
    // breaking ties differently across iterations and preventing the search from
    // getting stuck in local optima due to deterministic tie-breaking.
    for (int customer_id : customers) {
        // Generate a small random float in the range [-0.01, 0.01] (or similar)
        // This is a fast random number generation specifically for floats [0,1).
        float random_noise = getRandomFractionFast() * 0.02f - 0.01f; 

        // The score is primarily the time window width plus a small random noise.
        // Sorting these scores in ascending order means customers with smaller (tighter)
        // time windows will be prioritized for reinsertion.
        scores.push_back(instance.TW_Width[customer_id] + random_noise);
    }

    // Use argsort to get the indices that would sort the scores vector.
    // This is more efficient than creating pairs and sorting.
    std::vector<int> p = argsort(scores);

    // Create a new vector for the sorted customers based on the argsort indices.
    std::vector<int> sorted_customers(customers.size());
    for (size_t i = 0; i < customers.size(); ++i) {
        sorted_customers[i] = customers[p[i]];
    }
    // Replace the original customers vector with the sorted one.
    customers = sorted_customers;
}