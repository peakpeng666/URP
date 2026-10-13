#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <cmath>     // For std::pow
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// Heuristic for Step 1: Customer selection
// Selects a subset of customers to remove. This heuristic aims to select customers
// that are spatially clustered while incorporating stochasticity for diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    const int min_customers_to_remove = 10;
    const int max_customers_to_remove = 25; // For 500 customers, 2-5%
    const int num_neighbors_to_consider = 50; // Max number of closest neighbors to check from adj list
    const float diversity_exponent = 3.0f; // Higher value biases more towards closer customers
    const float random_customer_fallback_chance = 0.08f; // Chance to pick a completely random unremoved customer

    int num_customers_to_remove = getRandomNumber(min_customers_to_remove, max_customers_to_remove);

    std::vector<int> removed_customers;
    std::unordered_set<int> removed_set; // For O(1) lookup of removed customers

    // 1. Pick a random seed customer to start the removal process
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    removed_customers.push_back(initial_seed);
    removed_set.insert(initial_seed);

    // 2. Iteratively add customers based on proximity to already removed customers, with stochasticity
    while (removed_customers.size() < num_customers_to_remove) {
        int next_customer_to_add = -1;

        // Option 1: Pick a completely random unremoved customer (fallback or for diversity)
        if (getRandomFractionFast() < random_customer_fallback_chance) {
            std::vector<int> unremoved_customers_pool;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (removed_set.find(i) == removed_set.end()) {
                    unremoved_customers_pool.push_back(i);
                }
            }
            if (!unremoved_customers_pool.empty()) {
                next_customer_to_add = unremoved_customers_pool[getRandomNumber(0, unremoved_customers_pool.size() - 1)];
            }
        }

        // Option 2 (primary): Pick a customer from the neighborhood of an already removed customer
        if (next_customer_to_add == -1) {
            // Select a random pivot customer from the currently removed set
            int pivot_idx = getRandomNumber(0, removed_customers.size() - 1);
            int pivot_customer = removed_customers[pivot_idx];

            std::vector<int> potential_next_customers;
            int num_neighbors_checked = 0;

            // Iterate through the pivot's closest neighbors (pre-sorted in adj list)
            for (int neighbor : sol.instance.adj[pivot_customer]) {
                if (neighbor == 0) continue; // Skip depot
                if (removed_set.find(neighbor) == removed_set.end()) { // If not already removed
                    potential_next_customers.push_back(neighbor);
                }
                num_neighbors_checked++;
                if (num_neighbors_checked >= num_neighbors_to_consider) break; // Limit the number of neighbors checked
            }

            if (!potential_next_customers.empty()) {
                float r = getRandomFractionFast();
                // Bias selection towards the beginning of the list (closer neighbors)
                int idx = static_cast<int>(std::pow(r, diversity_exponent) * potential_next_customers.size());
                next_customer_to_add = potential_next_customers[idx];
            } else {
                // If no unremoved neighbors found, try picking a completely random unremoved customer as a last resort
                std::vector<int> unremoved_customers_pool;
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (removed_set.find(i) == removed_set.end()) {
                        unremoved_customers_pool.push_back(i);
                    }
                }
                if (!unremoved_customers_pool.empty()) {
                    next_customer_to_add = unremoved_customers_pool[getRandomNumber(0, unremoved_customers_pool.size() - 1)];
                }
            }
        }

        if (next_customer_to_add != -1) {
            removed_customers.push_back(next_customer_to_add);
            removed_set.insert(next_customer_to_add);
        } else {
            // This case implies all customers might be removed or an edge case occurred.
            // Break to avoid infinite loop if no more customers can be added.
            break;
        }
    }

    return removed_customers;
}

// Heuristic for Step 3: Ordering of the removed customers for reinsertion
// Orders customers based on a "difficulty" score (e.g., tight time windows, long service times),
// with a stochastic component to introduce diversity in the reinsertion order.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    const float reinsertion_diversity_exponent = 3.0f; // Higher value biases more towards "harder" customers

    // Create pairs of (score, customer_id)
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        // Calculate a score: smaller TW_Width means tighter window (harder).
        // Larger serviceTime means longer service (harder).
        // We want to prioritize harder customers, so a lower score (more negative) indicates higher priority.
        float score = -instance.TW_Width[customer_id] - instance.serviceTime[customer_id];
        customer_scores.push_back({score, customer_id});
    }

    // Sort customers primarily by their score (ascending), which means "harder" customers come first
    std::sort(customer_scores.begin(), customer_scores.end());

    // Create a new vector for the reordered customers
    std::vector<int> reordered_customers;
    reordered_customers.reserve(customers.size());

    // Use a boolean array to efficiently track which customers have been reordered
    // Since customer IDs start from 1, size is numCustomers + 1. Initialize to false.
    std::vector<bool> used_in_reorder(instance.numCustomers + 1, false);

    // Iteratively select customers from the sorted list with a probabilistic bias
    for (size_t i = 0; i < customers.size(); ++i) {
        std::vector<int> current_candidates_for_selection;
        current_candidates_for_selection.reserve(customers.size() - i);

        // Populate candidates from the sorted list that haven't been used yet
        for (const auto& p : customer_scores) {
            int c_id = p.second;
            if (!used_in_reorder[c_id]) {
                current_candidates_for_selection.push_back(c_id);
            }
        }

        // If for some reason no candidates are left (shouldn't happen if customers.size() > i), break
        if (current_candidates_for_selection.empty()) {
            break;
        }

        // Apply stochastic selection: bias towards the beginning of current_candidates_for_selection
        // (which are the "harder" customers)
        float r = getRandomFractionFast();
        int idx = static_cast<int>(std::pow(r, reinsertion_diversity_exponent) * current_candidates_for_selection.size());

        int chosen_customer = current_candidates_for_selection[idx];

        reordered_customers.push_back(chosen_customer);
        used_in_reorder[chosen_customer] = true;
    }

    // Update the input 'customers' vector with the new reordered sequence
    customers = reordered_customers;
}