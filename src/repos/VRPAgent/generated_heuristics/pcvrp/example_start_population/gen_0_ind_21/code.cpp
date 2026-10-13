#include "AgentDesigned.h"
#include <vector>
#include <random>
#include <unordered_set>
#include <algorithm>
#include <utility>

#include "Utils.h"

// Constants for removal heuristics
// These define the range for the number of customers to remove in each iteration.
// For instances with 500+ customers, removing 10-40 customers represents a small percentage
// (2-8%), ensuring a focused but diverse perturbation.
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 40;

// A small positive value used to prevent division by zero or overly large values
// in score calculations where a denominator might approach zero.
const float EPSILON = 1e-6;


// Step 1: Customer selection
// This heuristic selects a subset of customers to remove from the current solution.
// It aims to select customers that are "connected" to each other, fostering more
// localized and potentially meaningful changes during the reinsertion phase.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    int numCustomers = sol.instance.numCustomers;

    // Determine the number of customers to remove in this iteration,
    // ensuring it's within the defined range and doesn't exceed total customers.
    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    if (numCustomersToRemove > numCustomers) {
        numCustomersToRemove = numCustomers;
    }

    // 1. Select an initial seed customer randomly from all available customers (1 to numCustomers).
    // This allows unvisited customers to be selected and considered for reinsertion.
    int initial_seed_customer = getRandomNumber(1, numCustomers);
    selectedCustomersSet.insert(initial_seed_customer);

    // This vector holds the IDs of currently selected customers and is used to
    // randomly pick a "focus customer" for neighborhood expansion.
    std::vector<int> current_selected_vector;
    current_selected_vector.reserve(numCustomersToRemove); // Pre-allocate for efficiency
    current_selected_vector.push_back(initial_seed_customer);

    // 2. Iteratively select additional customers by expanding from already selected ones.
    // This maintains the property that selected customers are generally close to others in the set.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // Randomly pick a focus customer from the *already selected* customers.
        // This ensures the neighborhood search expands from existing clusters.
        int focus_customer_idx = getRandomNumber(0, static_cast<int>(current_selected_vector.size()) - 1);
        int focus_customer = current_selected_vector[focus_customer_idx];

        bool customer_added_in_this_iteration = false;

        // Iterate through the neighbors of the focus customer (sorted by distance in instance.adj).
        // Attempt to select the closest unselected neighbor.
        const std::vector<int>& neighbors = sol.instance.adj[focus_customer];
        for (int neighbor_id : neighbors) {
            // Check if the neighbor is a valid customer ID (not depot 0) and not already selected.
            if (neighbor_id >= 1 && neighbor_id <= numCustomers && selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(neighbor_id);
                current_selected_vector.push_back(neighbor_id); // Add to vector for future focus selection
                customer_added_in_this_iteration = true;
                break; // One customer added, move to the next iteration of the while loop
            }
        }

        // If no suitable unselected neighbor was found from the `focus_customer`'s adjacency list
        // (e.g., all its neighbors are already selected, or it has no valid neighbors),
        // select a completely random unselected customer to ensure progress and maintain diversity.
        if (!customer_added_in_this_iteration) {
            int random_unselected_customer;
            do {
                random_unselected_customer = getRandomNumber(1, numCustomers);
            } while (selectedCustomersSet.find(random_unselected_customer) != selectedCustomersSet.end());

            selectedCustomersSet.insert(random_unselected_customer);
            current_selected_vector.push_back(random_unselected_customer);
        }
    }

    // Convert the unordered_set to a vector for the return type.
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Step 3: Ordering of the removed customers
// This heuristic determines the order in which the removed customers will be reinserted.
// It prioritizes customers that offer a high prize and are relatively "easy" to insert
// due to their proximity to other nodes, potentially reducing reinsertion costs.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // A vector to store pairs of (score, customer_id) for sorting.
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size()); // Pre-allocate for efficiency

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float effective_cost_proxy = 0.0f;

        // Estimate reinsertion "difficulty" or "cost" using proximity.
        // We use the distance to the closest neighbor as a simple, fast proxy.
        if (!instance.adj[customer_id].empty()) {
            int closest_neighbor_id = instance.adj[customer_id][0];
            effective_cost_proxy = instance.distanceMatrix[customer_id][closest_neighbor_id];
        } else {
            // If a customer has no entries in its adjacency list (should be rare for valid VRP instances),
            // treat its effective cost proxy as zero, so only prize dictates its score.
            effective_cost_proxy = 0.0f;
        }

        // Calculate a score: Higher score means higher priority for reinsertion.
        // The score balances the customer's prize with its estimated proximity cost.
        // `prize / (effective_cost_proxy + 1.0f + EPSILON)`:
        // - Adding 1.0f ensures the denominator is at least 1.0f, preventing excessively large scores
        //   from very small (or zero) effective_cost_proxy values, which might destabilize the sorting.
        // - `EPSILON` guards against division by zero if `effective_cost_proxy` were exactly -1.0f (not expected).
        float score = prize / (effective_cost_proxy + 1.0f + EPSILON);

        // Add a small random perturbation to the score.
        // This introduces stochasticity, helping to break ties and ensuring diversity in the search
        // over millions of iterations, preventing premature convergence to local optima.
        // `getRandomFractionFast()` returns a float in [0, 1). Scaling `* 0.2f - 0.1f` maps it to [-0.1, 0.1).
        score += getRandomFractionFast() * 0.2f - 0.1f; 

        scored_customers.push_back({score, customer_id});
    }

    // Sort the customers in descending order based on their calculated scores.
    // Customers with higher scores (high prize, low effective cost proxy) are placed first.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original `customers` vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}