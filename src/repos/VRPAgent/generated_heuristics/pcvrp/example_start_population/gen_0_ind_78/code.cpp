#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>

// Assuming Utils.h is included via AgentDesigned.h or directly for getRandomNumber, getRandomFractionFast.

// Helper structure for sorting customers in sort_by_llm_1
struct CustomerSortInfo {
    int id;
    float score;
};

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_to_remove = getRandomNumber(10, 20); // Determine the number of customers to remove

    std::unordered_set<int> selected_customers_set; // For efficient lookup of already selected customers
    std::vector<int> selected_customers_vec;       // For returning the ordered list of selected customers

    // 1. Select an initial seed customer randomly
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(seed_customer);
    selected_customers_vec.push_back(seed_customer);

    // 2. Iteratively expand the selection based on proximity to already selected customers
    while (selected_customers_vec.size() < num_to_remove) {
        std::vector<int> candidates_for_next_add; // Pool of potential next customers based on proximity

        // Hyperparameter: how many closest neighbors to consider from 'adj' list for each selected customer
        // A larger value allows more spread candidates, a smaller value leads to tighter clusters.
        int k_neighbors_to_sample = 5; 

        // For each already selected customer, add a few of its closest unselected neighbors to the candidates pool
        for (int current_selected_id : selected_customers_vec) {
            int neighbors_added_from_this_customer = 0;
            // The adj list in Instance is pre-sorted by distance, so iterating from the beginning gives closest neighbors.
            for (int neighbor : sol.instance.adj[current_selected_id]) {
                if (neighbor == 0) continue; // Skip the depot node (node 0)
                if (selected_customers_set.count(neighbor)) continue; // Skip customers already selected

                candidates_for_next_add.push_back(neighbor);
                neighbors_added_from_this_customer++;
                if (neighbors_added_from_this_customer >= k_neighbors_to_sample) {
                    break; // Stop adding neighbors from this specific current_selected_id after 'k_neighbors_to_sample'
                }
            }
        }

        int chosen_to_add;
        if (candidates_for_next_add.empty()) {
            // Fallback: If no suitable close neighbors were found (e.g., all neighbors are already selected,
            // or the current cluster is isolated, or simply few customers overall).
            // In this case, pick a completely random unselected customer to ensure the process continues.
            std::vector<int> all_unselected_customers_fallback;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (!selected_customers_set.count(i)) {
                    all_unselected_customers_fallback.push_back(i);
                }
            }
            if (all_unselected_customers_fallback.empty()) {
                // This scenario indicates that num_to_remove is larger than the total available customers,
                // or all customers have already been selected.
                break; // No more customers to select, exit the loop
            }
            // Pick a random customer from all remaining unselected ones
            chosen_to_add = all_unselected_customers_fallback[getRandomNumber(0, all_unselected_customers_fallback.size() - 1)];
        } else {
            // Stochastic selection: Pick one randomly from the gathered pool of proximal candidates
            chosen_to_add = candidates_for_next_add[getRandomNumber(0, candidates_for_next_add.size() - 1)];
        }

        selected_customers_set.insert(chosen_to_add);
        selected_customers_vec.push_back(chosen_to_add);
    }

    return selected_customers_vec;
}

// Ordering heuristic for the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<CustomerSortInfo> customer_infos;
    customer_infos.reserve(customers.size()); // Reserve space for efficiency

    for (int customer_id : customers) {
        // Base score: Customer prize. Maximizing prize is a core objective.
        // Higher prize customers are generally more critical to reinsert.
        float score = instance.prizes[customer_id]; 

        // Add a small random perturbation to the score.
        // This introduces stochasticity, ensuring that customers with similar (or identical) prizes
        // get varied relative orderings across different iterations. This is crucial for diversity.
        // The magnitude of the random noise (scaled by total_prizes * 0.005f) is chosen to be small
        // enough that the primary prize-based sorting remains dominant, but large enough to effectively
        // shuffle customers with very close or equal prize values.
        float random_noise_magnitude = instance.total_prizes * 0.005f; 
        score += getRandomFractionFast() * random_noise_magnitude;
        
        customer_infos.push_back({customer_id, score});
    }

    // Sort customers in descending order of their calculated score.
    // Customers with higher prizes (and potentially higher random noise) will be prioritized for reinsertion.
    std::sort(customer_infos.begin(), customer_infos.end(), [](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        return a.score > b.score;
    });

    // Update the original 'customers' vector with the new sorted order of customer IDs
    for (size_t i = 0; i < customer_infos.size(); ++i) {
        customers[i] = customer_infos[i].id;
    }
}