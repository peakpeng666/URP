#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort, std::min
#include <vector> // For std::vector
#include <utility> // For std::pair
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> current_selection_vector; // Stores selected customers to easily pick a random one for growth

    // Determine the number of customers to remove (stochastic)
    // For 500 customers, removing 5-15 seems appropriate for "small number"
    int numCustomersToRemove = getRandomNumber(5, 15); 
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) { // Ensure at least one customer is selected if possible
        numCustomersToRemove = 1;
    } else if (sol.instance.numCustomers == 0) { // No customers to select
        return {};
    }

    // Phase 1: Initial seed selection (guarantees at least one customer)
    int first_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(first_customer);
    current_selection_vector.push_back(first_customer);

    // Phase 2: Growth phase - add customers close to already selected ones
    // This loop tries to find new neighbors a few times before resorting to random selection
    int attempts_to_grow = 0;
    int max_growth_attempts_per_add = 10; // Max attempts to find a suitable neighbor for a spot
    int total_growth_attempts = 0;
    int max_total_growth_attempts = numCustomersToRemove * max_growth_attempts_per_add * 2; // Upper bound

    while (selected_set.size() < numCustomersToRemove && total_growth_attempts < max_total_growth_attempts) {
        total_growth_attempts++;

        if (current_selection_vector.empty()) { // Should not happen after initial seed
            break;
        }

        // Pick a random customer from the *already selected* set to grow from
        int source_customer_idx = current_selection_vector[getRandomNumber(0, current_selection_vector.size() - 1)];

        const auto& adj_list = sol.instance.adj[source_customer_idx];
        if (adj_list.empty()) { // Customer has no neighbors (unlikely for VRP nodes)
            attempts_to_grow++;
            continue;
        }

        // Randomly pick a neighbor from the first few closest neighbors to ensure proximity but also stochasticity.
        // Considering up to 10 closest neighbors (index 0 to 9) to balance speed and quality.
        int neighbor_search_range = std::min((int)adj_list.size() - 1, 9); 
        if (neighbor_search_range < 0) { // No neighbors within the search range
            attempts_to_grow++;
            continue;
        }

        int new_customer_candidate = adj_list[getRandomNumber(0, neighbor_search_range)];

        // Ensure it's a customer (not depot, which is node 0) and not already selected.
        if (new_customer_candidate != 0 && selected_set.find(new_customer_candidate) == selected_set.end()) {
            selected_set.insert(new_customer_candidate);
            current_selection_vector.push_back(new_customer_candidate); // New customer also becomes a source for future growth
            attempts_to_grow = 0; // Reset attempts on successful addition
        } else {
            attempts_to_grow++;
        }

        // If we've tried too many times to grow from existing customers,
        // it might mean isolated selected customers or high density areas.
        // Fallback to random if growth is stuck.
        if (attempts_to_grow >= max_growth_attempts_per_add) {
            int random_customer = getRandomNumber(1, sol.instance.numCustomers);
            if (selected_set.find(random_customer) == selected_set.end()) {
                selected_set.insert(random_customer);
                current_selection_vector.push_back(random_customer); // Add to potential sources for next step too
                attempts_to_grow = 0; // Reset attempts on successful addition
            }
        }
    }

    // Fallback: If after all attempts we still haven't reached the target number, fill with random customers
    while (selected_set.size() < numCustomersToRemove) {
        int random_customer = getRandomNumber(1, sol.instance.numCustomers);
        selected_set.insert(random_customer);
    }

    return std::vector<int>(selected_set.begin(), selected_set.end());
}


// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Generate random weights for different criteria to introduce stochasticity
    // Normalize weights to avoid extreme biases if desired, but sum of random fractions is usually sufficient
    float w_demand = getRandomFractionFast();
    float w_dist_depot = getRandomFractionFast();
    float w_proximity_to_removed = getRandomFractionFast();
    float w_random_noise = getRandomFractionFast();

    // Prepare a vector of pairs (score, customer_id) for sorting
    std::vector<std::pair<float, int>> customer_scores(customers.size());

    for (size_t i = 0; i < customers.size(); ++i) {
        int current_customer_id = customers[i];
        float score = 0.0f;

        // Criterion 1: Demand
        // Higher demand gets higher score (prioritize larger items)
        score += w_demand * instance.demand[current_customer_id];

        // Criterion 2: Distance to Depot
        // Farther from depot gets higher score (prioritize isolated/far items)
        score += w_dist_depot * instance.distanceMatrix[0][current_customer_id];

        // Criterion 3: Proximity to other removed customers
        // Sum of distances to other customers in the *removed* set.
        // A higher sum means the customer is more "isolated" within the removed set,
        // which might indicate it's harder to re-insert or needs special attention.
        float sum_dist_other_removed = 0.0f;
        for (int other_customer_id : customers) {
            if (current_customer_id != other_customer_id) {
                sum_dist_other_removed += instance.distanceMatrix[current_customer_id][other_customer_id];
            }
        }
        score += w_proximity_to_removed * sum_dist_other_removed;

        // Criterion 4: Random noise for tie-breaking and additional diversity
        score += w_random_noise * getRandomFractionFast();

        customer_scores[i] = {score, current_customer_id};
    }

    // Sort customers based on their calculated scores in descending order.
    // This means customers with higher scores (e.g., higher demand, farther from depot, more isolated among removed)
    // will be attempted for reinsertion first.
    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort in descending order of score
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}