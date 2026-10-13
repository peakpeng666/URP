#include "AgentDesigned.h"
// AgentDesigned.h is assumed to include <random>, <unordered_set>, and "Utils.h"

// Customer selection heuristic
// This heuristic selects a small, connected group of customers
// for removal to encourage meaningful local search.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selected_customers_vec;
    std::unordered_set<int> selected_customers_set;

    // Determine the number of customers to remove.
    // A small fixed range is chosen to keep the neighborhood size manageable.
    // For 500 customers, 10-30 customers represent a small percentage (2-6%).
    int num_to_remove = getRandomNumber(10, 30);
    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) { // Ensure at least one if customers exist
        num_to_remove = 1;
    }

    if (num_to_remove == 0) { // No customers to remove
        return {};
    }

    // 1. Pick a random initial customer to seed the removal set.
    int start_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_vec.push_back(start_customer);
    selected_customers_set.insert(start_customer);

    // 2. Iteratively expand the set by adding neighbors of already selected customers.
    // This creates a "connected" group.
    int attempts_to_expand_from_neighbors = 0; // Counter to prevent infinite loops if all neighbors are selected

    while (selected_customers_vec.size() < num_to_remove) {
        bool added_new_customer_in_iteration = false;
        
        // Randomly pick a customer from the already selected set to try and expand from.
        // This ensures the "cluster" can grow from any point within itself, not just the newest addition.
        int pivot_idx = getRandomNumber(0, selected_customers_vec.size() - 1);
        int pivot_customer = selected_customers_vec[pivot_idx];

        // Consider the top K nearest neighbors of the pivot customer.
        // The adj list is pre-sorted by distance.
        const int MAX_NEIGHBORS_TO_CONSIDER = 10;
        for (int i = 0; i < sol.instance.adj[pivot_customer].size() && i < MAX_NEIGHBORS_TO_CONSIDER; ++i) {
            int neighbor_node = sol.instance.adj[pivot_customer][i];

            // Ensure the neighbor is a customer (not depot, node 0) and not already selected.
            if (neighbor_node != 0 && selected_customers_set.find(neighbor_node) == selected_customers_set.end()) {
                selected_customers_vec.push_back(neighbor_node);
                selected_customers_set.insert(neighbor_node);
                added_new_customer_in_iteration = true;
                attempts_to_expand_from_neighbors = 0; // Reset counter on success
                break; // Found and added a new customer, move to next iteration of outer loop
            }
        }

        // If no new customer was added from neighbors of the pivot customer,
        // it means all its top neighbors are already selected or are depots.
        // To guarantee progress and diversification, pick a completely random unselected customer.
        if (!added_new_customer_in_iteration) {
            attempts_to_expand_from_neighbors++;

            // After a few failed attempts to expand from existing neighbors,
            // pick a new random customer not already in the set.
            // This ensures we always reach `num_to_remove` and prevents stagnation.
            if (attempts_to_expand_from_neighbors >= 3) { // Threshold for trying to expand locally
                int random_customer_attempts = 0;
                while (random_customer_attempts < sol.instance.numCustomers) { // Safety break
                    int temp_customer = getRandomNumber(1, sol.instance.numCustomers);
                    if (selected_customers_set.find(temp_customer) == selected_customers_set.end()) {
                        selected_customers_vec.push_back(temp_customer);
                        selected_customers_set.insert(temp_customer);
                        attempts_to_expand_from_neighbors = 0; // Reset counter
                        break;
                    }
                    random_customer_attempts++;
                }
            }
        }
    }

    return selected_customers_vec;
}

// Customer ordering heuristic for reinsertion
// This heuristic sorts customers based on a "difficulty" score
// and adds stochasticity to promote diversity in reinsertion order.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<float> scores;
    scores.reserve(customers.size());

    // Calculate a "difficulty score" for each customer.
    // Higher demand customers are generally harder to fit due to capacity constraints.
    // Customers far from the depot might also be harder to integrate into tours.
    // A small random perturbation is added to ensure stochasticity,
    // which helps in exploring different reinsertion orders over millions of iterations.
    const float DIST_DEPOT_WEIGHT = 0.01f; // Weight for distance from depot relative to demand
    const float STOCHASTIC_NOISE_MAGNITUDE = 0.1f; // Magnitude of random noise

    for (int customer_id : customers) {
        float score = (float)instance.demand[customer_id];
        score += instance.distanceMatrix[0][customer_id] * DIST_DEPOT_WEIGHT;
        score += getRandomFractionFast() * STOCHASTIC_NOISE_MAGNITUDE; // Add stochastic noise

        // Negate the score because argsort sorts in ascending order,
        // and we want to effectively sort in descending order of difficulty.
        scores.push_back(-score);
    }

    // Get the sorted indices based on the calculated scores.
    std::vector<int> sorted_indices = argsort(scores);

    // Create a new vector with customers sorted according to the indices.
    std::vector<int> sorted_customers_temp;
    sorted_customers_temp.reserve(customers.size());
    for (int idx : sorted_indices) {
        sorted_customers_temp.push_back(customers[idx]);
    }

    // Replace the original customers vector with the sorted one.
    customers = sorted_customers_temp;
}