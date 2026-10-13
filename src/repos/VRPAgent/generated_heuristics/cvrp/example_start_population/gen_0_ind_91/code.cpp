#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>

// Assumed to be provided by Utils.h
// int getRandomNumber(int min, int max);
// float getRandomFractionFast();


// Customer selection heuristic for the LNS framework.
// This function selects a subset of customers to be removed from the current solution.
// The selection aims to cluster removed customers while incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;

    // Determine the number of customers to remove.
    // A small range (10-20) is chosen to ensure fast iterations and localized perturbations
    // suitable for large instances.
    int numCustomersToRemove = getRandomNumber(10, 20);

    // Handle edge cases for very small instances or no customers.
    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // 1. Pick an initial seed customer randomly.
    // Customer IDs are typically 1-indexed (1 to numCustomers).
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer);

    // 2. Expand the set of selected customers until the desired number is reached.
    // This loop ensures that newly selected customers are often close to already selected ones,
    // promoting meaningful changes during reinsertion.
    while (selectedCustomers.size() < numCustomersToRemove) {
        // Create a temporary vector to allow random selection from the unordered_set.
        // This is necessary because unordered_set elements cannot be accessed by index directly.
        std::vector<int> current_selected_vector;
        current_selected_vector.reserve(selectedCustomers.size());
        for (int c : selectedCustomers) {
            current_selected_vector.push_back(c);
        }

        // If for some reason the selected set becomes empty (should not happen after seed insertion), break.
        if (current_selected_vector.empty()) {
            break;
        }

        // Randomly pick a customer from the *already selected* set.
        // This 'pivot' customer will be used to find a nearby new customer.
        int pivot_customer_idx = getRandomNumber(0, (int)current_selected_vector.size() - 1);
        int pivot_customer = current_selected_vector[pivot_customer_idx];

        // Access the adjacency list of the pivot customer.
        // The list `sol.instance.adj[pivot_customer]` contains neighbors sorted by distance.
        const std::vector<int>& neighbors = sol.instance.adj[pivot_customer];

        bool added_new_customer = false;
        // Consider a small, stochastic number of the closest neighbors for expansion.
        // This adds diversity to the selection process while maintaining proximity.
        int k_neighbors_to_consider = std::min((int)neighbors.size(), 5 + getRandomNumber(0, 5));

        // Find potential unselected neighbors among the top K closest ones.
        std::vector<int> potential_unselected_neighbors;
        for (int i = 0; i < k_neighbors_to_consider; ++i) {
            int neighbor_id = neighbors[i];
            if (selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                potential_unselected_neighbors.push_back(neighbor_id);
            }
        }

        // If there are unselected neighbors in the top K, randomly pick one and add it.
        if (!potential_unselected_neighbors.empty()) {
            int neighbor_to_add_idx = getRandomNumber(0, (int)potential_unselected_neighbors.size() - 1);
            selectedCustomers.insert(potential_unselected_neighbors[neighbor_to_add_idx]);
            added_new_customer = true;
        }

        // 3. Fallback mechanism: If no new customer was added from the vicinity of the pivot,
        // (e.g., all its closest neighbors are already selected),
        // add a completely random customer from the remaining unselected pool.
        // This ensures the loop always makes progress and prevents getting stuck,
        // even if it occasionally deviates from strict proximity.
        if (!added_new_customer) {
            int backup_random_customer_id = getRandomNumber(1, sol.instance.numCustomers);
            // Loop a few times to try and find an unselected random customer.
            int safety_counter = 0;
            while (selectedCustomers.find(backup_random_customer_id) != selectedCustomers.end() && safety_counter < 100) {
                backup_random_customer_id = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter++;
            }
            // If an unselected random customer is found after the attempts, add it.
            if (selectedCustomers.find(backup_random_customer_id) == selectedCustomers.end()) {
                selectedCustomers.insert(backup_random_customer_id);
            } else if (selectedCustomers.size() < sol.instance.numCustomers) {
                // Robust last resort: iterate sequentially to find the next available unselected customer.
                // This ensures progress even in very rare, difficult-to-select scenarios.
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (selectedCustomers.find(i) == selectedCustomers.end()) {
                        selectedCustomers.insert(i);
                        break;
                    }
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Ordering heuristic for the removed customers before greedy reinsertion.
// This function sorts the customers based on a composite score to prioritize
// "harder to place" customers first, allowing them to claim better spots.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Create a vector of pairs to store (score, customer_id).
    // This allows sorting based on the score while keeping track of the original customer ID.
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        // Calculate a score for each customer.
        // A higher score indicates that the customer is considered "harder to place"
        // or more critical for route structure, hence should be reinserted earlier.
        float score = 0.0f;

        // Ensure customer_id is a valid index before accessing instance data.
        // Customer IDs (1 to numCustomers) are valid for 0-indexed arrays like demand
        // and distanceMatrix, assuming index 0 is for the depot.
        if (customer_id >= 0 && customer_id < instance.numNodes) {
            // Factor 1: Customer demand. Higher demand means harder to fit.
            score += static_cast<float>(instance.demand[customer_id]);
            // Factor 2: Distance from the depot. Farther customers might imply longer tours.
            // Scaled by 0.1 to give demand more weight, but still incorporate distance.
            score += instance.distanceMatrix[0][customer_id] * 0.1f;
        }

        // Add a small random perturbation to the score.
        // This is crucial for introducing stochasticity into the sorting order.
        // It helps explore different reinsertion sequences for customers with similar scores,
        // providing necessary diversity over millions of LNS iterations.
        score += getRandomFractionFast() * 0.001f; // A small constant to ensure perturbation is minor

        customer_scores.push_back({score, customer_id});
    }

    // Sort the customers in descending order of their calculated scores.
    // Customers with higher scores (e.g., high demand, far from depot) will appear earlier in the list.
    std::sort(customer_scores.begin(), customer_scores.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; // Sort in descending order
              });

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}