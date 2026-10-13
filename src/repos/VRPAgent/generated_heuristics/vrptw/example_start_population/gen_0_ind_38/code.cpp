#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include <limits>    // For numeric_limits
#include "Utils.h"

// Customer selection heuristic
// This heuristic aims to select a small, spatially coherent cluster of customers
// to be removed, while incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // Determine the number of customers to remove, with a stochastic range
    int numCustomersToTryRemove = getRandomNumber(10, 25);
    const Instance& instance = sol.instance;

    // Ensure we don't try to remove more customers than available
    if (numCustomersToTryRemove == 0) {
        return {};
    }
    if (numCustomersToTryRemove > instance.numCustomers) {
        numCustomersToTryRemove = instance.numCustomers;
    }

    // 1. Pick a random customer as the initial seed for the cluster
    int seed_customer = getRandomNumber(1, instance.numCustomers);
    selectedCustomers.insert(seed_customer);

    // 2. Iteratively expand the cluster until the desired number of customers is met
    while (selectedCustomers.size() < numCustomersToTryRemove) {
        // Randomly pick an already selected customer to expand from.
        // This ensures new additions are typically close to existing selected customers.
        int current_source_customer_idx = getRandomNumber(0, (int)selectedCustomers.size() - 1);
        auto it = selectedCustomers.begin();
        std::advance(it, current_source_customer_idx);
        int source_customer = *it;

        bool added_customer_in_proximity = false;
        // Iterate through neighbors of the source_customer, sorted by distance (using instance.adj)
        // Try to add the closest unselected customer neighbor.
        for (int neighbor_node_idx : instance.adj[source_customer]) {
            // Check if the neighbor is a customer (not depot node 0) and not already selected
            if (neighbor_node_idx != 0 && selectedCustomers.find(neighbor_node_idx) == selectedCustomers.end()) {
                selectedCustomers.insert(neighbor_node_idx);
                added_customer_in_proximity = true;
                break; // Found and added a close, unselected customer, move to next iteration
            }
        }

        // Fallback: If no suitable unselected neighbor was found for any selected customer,
        // (e.g., all neighbors are already selected, or customer is isolated)
        // then pick a completely random unselected customer to ensure progress.
        if (!added_customer_in_proximity) {
            int random_unselected_customer;
            int attempts = 0;
            const int max_attempts = 100; // Prevent infinite loop in very rare edge cases

            do {
                random_unselected_customer = getRandomNumber(1, instance.numCustomers);
                attempts++;
                if (attempts > max_attempts && selectedCustomers.size() < instance.numCustomers) {
                    // Fallback to iterating if random attempts fail too many times on large sets
                    for(int i=1; i <= instance.numCustomers; ++i) {
                        if (selectedCustomers.find(i) == selectedCustomers.end()) {
                            random_unselected_customer = i;
                            break;
                        }
                    }
                }
            } while (selectedCustomers.find(random_unselected_customer) != selectedCustomers.end() && selectedCustomers.size() < instance.numCustomers);
            
            // Only insert if we actually found an unselected customer (i.e., not all customers are selected)
            if (selectedCustomers.size() < instance.numCustomers) {
                selectedCustomers.insert(random_unselected_customer);
            } else {
                // All customers are selected, should not happen if numCustomersToTryRemove <= instance.numCustomers
                break; 
            }
        }
    }
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Ordering heuristic for removed customers
// This heuristic sorts customers based on a 'hardness' score, prioritizing
// customers that are typically more difficult to reinsert.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Define weights for different components of the 'hardness' score
    // These weights can be tuned to emphasize certain characteristics
    const float TW_TIGHTNESS_WEIGHT = 1.0f;
    const float DEMAND_WEIGHT = 0.2f;
    const float SERVICE_TIME_WEIGHT = 0.3f;
    const float STOCHASTIC_NOISE_RANGE = 0.05f; // Small range for stochastic noise

    for (int customer_id : customers) {
        float score = 0.0f;

        // Component 1: Time Window Tightness
        // Customers with smaller time window widths are harder to place.
        // Add a small epsilon to the denominator to prevent division by zero or very large scores
        // if a time window width is 0 or extremely small.
        score += TW_TIGHTNESS_WEIGHT / (instance.TW_Width[customer_id] + 1e-6f);

        // Component 2: Demand
        // Customers with higher demand might be harder to fit into remaining vehicle capacity.
        score += DEMAND_WEIGHT * instance.demand[customer_id];

        // Component 3: Service Time
        // Customers with longer service times consume more route time, making them less flexible.
        score += SERVICE_TIME_WEIGHT * instance.serviceTime[customer_id];

        // Component 4: Stochasticity
        // Add a small random noise to the score to break ties and introduce diversity
        // across many LNS iterations, preventing deterministic reinsertion patterns.
        score += getRandomFraction(-STOCHASTIC_NOISE_RANGE, STOCHASTIC_NOISE_RANGE);

        scored_customers.emplace_back(score, customer_id);
    }

    // Sort the customers in descending order of their calculated score.
    // This places the 'hardest' customers at the beginning of the list,
    // so they are reinserted first during the greedy reinsertion step.
    std::sort(scored_customers.begin(), scored_customers.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    // Update the original customers vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}