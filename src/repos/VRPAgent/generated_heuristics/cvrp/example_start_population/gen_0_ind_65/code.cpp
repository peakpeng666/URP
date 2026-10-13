#include "AgentDesigned.h"
#include <random> 
#include <unordered_set>
#include <vector>
#include <algorithm> 
#include <utility> // For std::pair

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    
    // Determine the number of customers to remove.
    // The range is chosen to be small but provide variety for large instances.
    // It's capped to ensure it doesn't exceed available customers.
    int numCustomersToRemove = getRandomNumber(15, std::min(40, sol.instance.numCustomers));

    if (sol.instance.numCustomers == 0) {
        return {}; // No customers to remove
    }

    // Step 1: Select a random seed customer to start the removal process.
    // Customer IDs are typically 1-indexed, so we ensure the range is correct.
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers); 
    selectedCustomers.insert(seed_customer);

    // Step 2: Iteratively expand the set of removed customers by prioritizing neighbors
    // of already selected customers. This encourages spatial connectivity among removed customers.
    while (selectedCustomers.size() < numCustomersToRemove) {
        bool customer_added_in_this_iteration = false;

        // Convert the set of currently selected customers to a vector to allow random access.
        // This is efficient as the number of selected customers is small.
        std::vector<int> current_selected_vec(selectedCustomers.begin(), selectedCustomers.end());

        // Attempt to add a neighbor of an already selected customer.
        if (!current_selected_vec.empty()) {
            // Pick a random "pivot" customer from the already selected ones.
            int pivot_customer_idx_in_vec = getRandomNumber(0, (int)current_selected_vec.size() - 1);
            int pivot_customer = current_selected_vec[pivot_customer_idx_in_vec];

            // Iterate through a few of its closest neighbors (e.g., first 10 from the adjacency list)
            // and stochastically attempt to add one.
            const auto& neighbors = sol.instance.adj[pivot_customer];
            int neighbors_to_check = std::min((int)neighbors.size(), 10); 

            for (int i = 0; i < neighbors_to_check; ++i) {
                int neighbor_id = neighbors[i];
                // Ensure the neighbor is a customer (ID > 0) and not already selected.
                if (neighbor_id > 0 && selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                    // Stochastic acceptance: add the neighbor with a certain probability (e.g., 80%).
                    // This adds diversity to the selection process.
                    if (getRandomFractionFast() < 0.8) { 
                        selectedCustomers.insert(neighbor_id);
                        customer_added_in_this_iteration = true;
                        break; // Successfully added a customer, break and proceed to fill quota.
                    }
                }
            }
        }

        // Fallback: If no neighbor was added (e.g., all neighbors were already selected,
        // or stochastic acceptance failed repeatedly), pick a truly random unselected customer.
        // This ensures the target number of customers to remove is always met.
        if (!customer_added_in_this_iteration) {
            int random_cust = getRandomNumber(1, sol.instance.numCustomers);
            // Loop until an unselected customer is found.
            while (selectedCustomers.count(random_cust)) {
                random_cust = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(random_cust);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Ordering heuristic for removed customers before greedy reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // A temporary vector to store (score, customer_id) pairs.
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Create a hash set of the customers to be removed for efficient lookup
    // when checking for proximity to other removed customers.
    std::unordered_set<int> removed_set(customers.begin(), customers.end());

    // Calculate a score for each customer.
    // The score prioritizes customers that are "harder" to place (e.g., high demand)
    // or those that might "anchor" new structures (e.g., central to the removed set).
    // A small stochastic component is added for diversity.
    for (int customer_id : customers) {
        float score = 0.0f;

        // Component 1: Demand of the customer. Higher demand customers are often
        // more difficult to reinsert due to capacity constraints.
        // Multiply by a large factor to make it the primary sorting criterion.
        score += static_cast<float>(instance.demand[customer_id]) * 100.0f;

        // Component 2: Proximity to other removed customers.
        // Customers that are close to many other removed customers might be good to
        // reinsert first to help form coherent new routes or extend existing ones.
        int removed_neighbors_count = 0;
        const auto& neighbors = instance.adj[customer_id];
        // Check a small number of its closest neighbors (e.g., top 5) from the adjacency list.
        int neighbors_to_check = std::min((int)neighbors.size(), 5);

        for (int i = 0; i < neighbors_to_check; ++i) {
            int neighbor_id = neighbors[i];
            // If the neighbor is also one of the customers being reinserted, increment count.
            if (neighbor_id > 0 && removed_set.count(neighbor_id)) {
                removed_neighbors_count++;
            }
        }
        // Add to score, scaled to be less dominant than demand but still significant.
        score += static_cast<float>(removed_neighbors_count) * 50.0f; 

        // Component 3: Stochastic perturbation.
        // A small random value is added to break ties and introduce variety across iterations,
        // which is crucial for exploration in LNS.
        score += getRandomFractionFast(); // Adds a value between 0.0 and 1.0

        scored_customers.push_back({score, customer_id});
    }

    // Sort the customers in descending order based on their calculated scores.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort from highest score to lowest score.
    });

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < scored_customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}