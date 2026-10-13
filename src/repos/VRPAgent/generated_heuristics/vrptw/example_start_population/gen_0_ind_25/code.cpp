#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort and std::min
#include "Utils.h"   // For getRandomNumber, getRandomFraction

// Heuristic for Step 1: Customer selection
// Selects a subset of customers to remove from the current solution.
// The selection aims to gather customers that are geographically close to each other,
// while incorporating stochasticity for diverse exploration.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_customers;

    // Define the range for the number of customers to remove.
    // This range is suitable for large instances like 500 customers,
    // keeping the removal subset small as required.
    const int MIN_REMOVE = 10;
    const int MAX_REMOVE = 25; 
    
    int num_to_remove = getRandomNumber(MIN_REMOVE, MAX_REMOVE);
    // Ensure we don't try to remove more customers than available
    num_to_remove = std::min(num_to_remove, sol.instance.numCustomers);

    if (num_to_remove == 0) {
        return {}; // Nothing to remove
    }

    // Add the initial random customer to start the cluster.
    // Customer IDs are typically 1-indexed, so 1 to numCustomers.
    int first_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(first_customer);
    selected_customers.push_back(first_customer);

    // Iteratively add more customers until the target number is reached.
    // Prioritize adding neighbors of already selected customers to ensure proximity.
    while (selected_customers.size() < num_to_remove) {
        bool added_neighbor_in_this_step = false;
        
        // Randomly select a pivot customer from the currently selected set.
        // This pivot customer's neighbors will be considered for the next addition.
        int pivot_idx = getRandomNumber(0, selected_customers.size() - 1);
        int pivot_customer = selected_customers[pivot_idx];

        // Define how many of the closest neighbors to consider.
        // instance.adj provides neighbors pre-sorted by distance.
        const int NEIGHBOR_CONSIDER_COUNT = 5; 

        // Iterate through the closest neighbors of the pivot customer.
        for (int i = 0; i < std::min((int)sol.instance.adj[pivot_customer].size(), NEIGHBOR_CONSIDER_COUNT); ++i) {
            int neighbor_customer = sol.instance.adj[pivot_customer][i];

            // Ensure the neighbor is a valid customer (not depot) and not already selected.
            // Customer IDs are 1 to numCustomers.
            if (neighbor_customer >= 1 && neighbor_customer <= sol.instance.numCustomers &&
                selected_set.find(neighbor_customer) == selected_set.end()) { 
                
                // Introduce stochasticity: High probability to add a close neighbor.
                // This balances locality with some randomness for exploration.
                if (getRandomFraction() < 0.85) { // 85% chance to add this neighbor
                    selected_set.insert(neighbor_customer);
                    selected_customers.push_back(neighbor_customer);
                    added_neighbor_in_this_step = true;
                    break; // Move to selecting the next customer for removal
                }
            }
        }

        // Fallback mechanism: If no neighbor was added (e.g., all close neighbors already selected,
        // or probabilistic check failed), or to introduce more diversity into the cluster,
        // add a completely random unselected customer.
        if (!added_neighbor_in_this_step) {
            int random_customer_attempts = 0;
            int new_random_customer;
            do {
                new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
                random_customer_attempts++;
                // Safeguard against infinite loops if almost all customers are selected
                if (random_customer_attempts > sol.instance.numCustomers * 2) { 
                    break; 
                }
            } while (selected_set.find(new_random_customer) != selected_set.end());

            if (selected_set.find(new_random_customer) == selected_set.end()) {
                selected_set.insert(new_random_customer);
                selected_customers.push_back(new_random_customer);
            }
        }
    }
    return selected_customers;
}

// Heuristic for Step 3: Ordering of the removed customers for reinsertion.
// Sorts the given list of customers based on a measure of "inflexibility",
// specifically their time window width, with stochastic noise to ensure diversity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Sort customers in place using a lambda function.
    // The primary sorting criterion is the time window width (TW_Width).
    // Customers with smaller (tighter) time windows are considered "harder" to place,
    // and are prioritized for earlier reinsertion. This can help prevent them from
    // becoming unfeasible later.
    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        float tw1 = instance.TW_Width[c1];
        float tw2 = instance.TW_Width[c2];

        // Introduce a small random component to the sorting key.
        // This ensures that customers with identical time window widths are
        // ordered stochastically, contributing to search diversity.
        // The scale of the noise is kept small to maintain the primary ordering.
        const float RANDOM_NOISE_SCALE = 0.001f; 
        float score1 = tw1 + getRandomFraction() * RANDOM_NOISE_SCALE;
        float score2 = tw2 + getRandomFraction() * RANDOM_NOISE_SCALE;

        // Sort in ascending order of (perturbed) time window width.
        // Smaller TW_Width means higher priority (inserted earlier).
        return score1 < score2;
    });
}