#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::min
#include <vector>
#include <cmath>     // For std::sqrt
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20); // Small number of customers

    std::unordered_set<int> selectedCustomers;
    std::vector<int> selected_vec; // To allow random access to selected customers

    // Step 1: Initial Seed - Pick a random customer
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initial_seed);
    selected_vec.push_back(initial_seed);

    int attempts_without_adding = 0;
    const int max_stagnation_attempts = 50; // Threshold to detect stagnation and inject new seed

    // Step 2: Expand from selected customers
    while (selectedCustomers.size() < numCustomersToRemove && selectedCustomers.size() < sol.instance.numCustomers) {
        bool added_current_iter = false;

        // Pick a random customer from the already selected set to expand from
        int c_source_idx = getRandomNumber(0, selected_vec.size() - 1);
        int c_source = selected_vec[c_source_idx];

        // Collect potential neighbors that are not yet selected
        std::vector<int> candidate_neighbors;
        // Limit the number of closest neighbors to check for speed and locality
        int num_neighbors_to_check = std::min((int)sol.instance.adj[c_source].size(), getRandomNumber(5, 15)); 

        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor_id = sol.instance.adj[c_source][i];
            if (selectedCustomers.count(neighbor_id) == 0) {
                candidate_neighbors.push_back(neighbor_id);
            }
        }

        // If there are candidate neighbors, randomly pick one and add it
        if (!candidate_neighbors.empty()) {
            int neighbor_to_add_idx = getRandomNumber(0, candidate_neighbors.size() - 1);
            int neighbor_to_add = candidate_neighbors[neighbor_to_add_idx];
            
            selectedCustomers.insert(neighbor_to_add);
            selected_vec.push_back(neighbor_to_add);
            added_current_iter = true;
            attempts_without_adding = 0; // Reset stagnation counter
        } else {
            attempts_without_adding++; // Increment if no neighbor could be added from c_source
        }

        // Step 3: Fallback - If stuck, inject a new random unselected customer
        if (!added_current_iter && attempts_without_adding > max_stagnation_attempts) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            int max_attempts_to_find_new_seed = sol.instance.numCustomers * 2; // Prevent infinite loop for sparse cases
            int current_find_attempts = 0;

            while (selectedCustomers.count(new_seed) && current_find_attempts < max_attempts_to_find_new_seed && selectedCustomers.size() < sol.instance.numCustomers) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                current_find_attempts++;
            }
            
            if (selectedCustomers.count(new_seed) == 0) {
                selectedCustomers.insert(new_seed);
                selected_vec.push_back(new_seed);
                attempts_without_adding = 0; // Reset stagnation counter
            } else {
                break; // Cannot find a new unselected customer, break to avoid infinite loop
            }
        }
    }

    return selected_vec;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    enum SortCriterion {
        X_COORD,
        Y_COORD,
        DIST_DEPOT,
        DEMAND
    };

    // Randomly choose sorting criterion and direction
    int choice = getRandomNumber(0, 7); // 4 criteria * 2 directions (ascending/descending)

    SortCriterion criterion;
    bool ascending; // true for ascending, false for descending

    if (choice == 0) { criterion = X_COORD; ascending = true; }
    else if (choice == 1) { criterion = X_COORD; ascending = false; }
    else if (choice == 2) { criterion = Y_COORD; ascending = true; }
    else if (choice == 3) { criterion = Y_COORD; ascending = false; }
    else if (choice == 4) { criterion = DIST_DEPOT; ascending = true; }
    else if (choice == 5) { criterion = DIST_DEPOT; ascending = false; }
    else if (choice == 6) { criterion = DEMAND; ascending = true; } // Low demand first
    else { criterion = DEMAND; ascending = false; } // High demand first

    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        float val1, val2;
        switch (criterion) {
            case X_COORD:
                val1 = instance.nodePositions[c1][0];
                val2 = instance.nodePositions[c2][0];
                break;
            case Y_COORD:
                val1 = instance.nodePositions[c1][1];
                val2 = instance.nodePositions[c2][1];
                break;
            case DIST_DEPOT:
                // Use pre-calculated distance matrix for speed
                val1 = instance.distanceMatrix[0][c1];
                val2 = instance.distanceMatrix[0][c2];
                break;
            case DEMAND:
                val1 = static_cast<float>(instance.demand[c1]);
                val2 = static_cast<float>(instance.demand[c2]);
                break;
        }

        if (ascending) {
            return val1 < val2;
        } else {
            return val1 > val2;
        }
    });
}