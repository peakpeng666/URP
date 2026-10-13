#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::shuffle
#include <vector> // Required for std::vector
#include "Utils.h" // For getRandomNumber, getRandomFractionFast

// Customer selection heuristic
// Selects a subset of customers for removal.
// The selection aims to be somewhat "connected" or clustered, meaning
// each selected customer is close to at least one or a few other selected customers.
// Incorporates stochastic behavior for diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    // Stores customers already selected that can be expanded from.
    // This helps maintain some connectivity in the removed set.
    std::vector<int> candidates_for_expansion; 

    // Determine the number of customers to remove.
    // Range is kept relatively small (10-20) to align with typical LNS practices for large instances,
    // ensuring the reinsertion phase is manageable while allowing meaningful changes.
    int num_to_remove = getRandomNumber(10, 20); 
    // Ensure we don't try to remove more customers than available.
    num_to_remove = std::min(num_to_remove, sol.instance.numCustomers);

    // Initial seed customer selection.
    // A random customer is chosen to start the removal process.
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_seed);
    candidates_for_expansion.push_back(initial_seed);

    // Iteratively expand the set of selected customers until the target size is reached.
    while (selected_customers_set.size() < num_to_remove) {
        bool added_new_customer_in_iter = false;

        // Strategy 1: Attempt to expand from an existing selected customer (preferential strategy).
        // This promotes the "connectedness" property of the removed set.
        if (!candidates_for_expansion.empty()) {
            // Pick a random customer from the candidates_for_expansion list.
            int rand_idx = getRandomNumber(0, candidates_for_expansion.size() - 1);
            int current_source_customer = candidates_for_expansion[rand_idx];

            // Iterate through a few of its closest neighbors (adj list is sorted by distance).
            // The number of neighbors checked is stochastic to add diversity.
            int neighbors_to_check = std::min((int)sol.instance.adj[current_source_customer].size(), getRandomNumber(3, 7)); 
            for (int i = 0; i < neighbors_to_check; ++i) {
                int neighbor_id = sol.instance.adj[current_source_customer][i];

                // Ensure the neighbor_id is a valid customer (not the depot, and within customer range).
                if (neighbor_id == 0 || neighbor_id > sol.instance.numCustomers) {
                    continue; 
                }

                // If the neighbor is not already selected, add it to the set.
                if (selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                    selected_customers_set.insert(neighbor_id);
                    // Add the newly selected customer to the list of potential sources for future expansion.
                    candidates_for_expansion.push_back(neighbor_id); 
                    added_new_customer_in_iter = true;

                    // Introduce stochasticity in how many neighbors are added from a single source.
                    // This prevents the selection from always "spreading" uniformly or too greedily.
                    if (getRandomFractionFast() < 0.6) { // 60% chance to break after adding one neighbor
                        break; 
                    }
                    if (selected_customers_set.size() == num_to_remove) { // Check if target size reached
                        break; 
                    }
                }
                if (selected_customers_set.size() == num_to_remove) {
                    break;
                }
            }
        }

        // Strategy 2: If no new customer was added via expansion from existing candidates,
        // or if the candidates_for_expansion list was empty,
        // pick a new random unselected customer as a seed.
        // This ensures progress towards `num_to_remove` and introduces diversity by allowing
        // for multiple disconnected "clusters" of removed customers.
        if (!added_new_customer_in_iter && selected_customers_set.size() < num_to_remove) {
            int new_seed_customer = -1;
            // Attempt to find an unselected customer for a limited number of tries.
            for (int attempt = 0; attempt < 50; ++attempt) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(potential_seed) == selected_customers_set.end()) {
                    new_seed_customer = potential_seed;
                    break;
                }
            }
            // If a new seed was found, add it.
            if (new_seed_customer != -1) {
                selected_customers_set.insert(new_seed_customer);
                candidates_for_expansion.push_back(new_seed_customer);
            } else {
                // Should theoretically not happen for reasonable num_to_remove.
                // Breaks the loop if no more unselected customers can be found.
                break; 
            }
        }
    }

    // Convert the unordered_set to a vector before returning.
    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}


// Customer ordering heuristic
// Sorts the removed customers, influencing the order in which they are reinserted.
// Uses different stochastic sorting strategies to promote diversity in the search.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Randomly select a sorting strategy.
    // This stochastic choice ensures a wide exploration of reinsertion orders over many iterations.
    // 0: Sort by combined difficulty (high demand + high distance from depot first)
    // 1: Sort by combined ease (low demand + low distance from depot first)
    // 2: Pure random shuffle (baseline for maximum diversity)
    // 3: Sort by demand (high demand customers first)
    // 4: Sort by distance from depot (customers far from the depot first)
    int sorting_strategy = getRandomNumber(0, 4);

    if (sorting_strategy == 0) { // Sort by difficulty (higher demand and/or farther from depot first)
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float score1 = (float)instance.demand[c1] + instance.distanceMatrix[0][c1];
            float score2 = (float)instance.demand[c2] + instance.distanceMatrix[0][c2];
            return score1 > score2; // Descending order of score
        });
    } else if (sorting_strategy == 1) { // Sort by ease (lower demand and/or closer to depot first)
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float score1 = (float)instance.demand[c1] + instance.distanceMatrix[0][c1];
            float score2 = (float)instance.demand[c2] + instance.distanceMatrix[0][c2];
            return score1 < score2; // Ascending order of score
        });
    } else if (sorting_strategy == 3) { // Sort by demand (higher demand first)
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.demand[c1] > instance.demand[c2]; // Descending order of demand
        });
    } else if (sorting_strategy == 4) { // Sort by distance from depot (farther from depot first)
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] > instance.distanceMatrix[0][c2]; // Descending order of distance
        });
    } else { // sorting_strategy == 2: Pure random shuffle
        // Use a thread_local random number generator for better performance and thread safety.
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}