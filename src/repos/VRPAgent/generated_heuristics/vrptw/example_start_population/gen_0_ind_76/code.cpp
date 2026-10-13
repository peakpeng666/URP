#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort
#include "Utils.h" // For getRandomNumber, getRandomFraction

// Heuristic for Step 1: Customer Selection
// This function selects a subset of customers to remove from the current solution.
// The goal is to select a small number of customers that are somewhat geographically
// clustered to encourage meaningful changes during reinsertion. Stochasticity is
// introduced by random starting points and random selection from candidate neighbors.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set; // To ensure uniqueness and fast lookup
    std::vector<int> result_customers; // The final list of selected customer IDs

    // Determine the number of customers to remove. Keep it small for LNS.
    // A range of 10 to 20 customers is suitable for instances of 500+ customers.
    int num_to_remove = getRandomNumber(10, 20);

    // Constant to limit exploration of neighbors. This helps maintain speed
    // and focuses on relatively close neighbors, ensuring locality.
    const int K_NEIGHBORS_TO_CONSIDER = 30;

    // 1. Pick a random starting customer to initiate the removal "cluster".
    int start_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(start_customer);
    result_customers.push_back(start_customer);

    // Maintain a list of candidates from which to pick subsequent customers.
    // Neighbors of already selected customers are added here. Duplicates are fine
    // as they naturally increase the probability of selecting customers in dense regions.
    std::vector<int> current_candidates;

    // Add the initial neighbors of the starting customer to the candidate pool.
    // Since adj is sorted by distance, we pick the closest ones first.
    int neighbors_added = 0;
    for (int neighbor_node : sol.instance.adj[start_customer]) {
        if (neighbor_node == 0) continue; // Skip the depot
        if (selected_customers_set.find(neighbor_node) == selected_customers_set.end()) {
            current_candidates.push_back(neighbor_node);
            neighbors_added++;
            if (neighbors_added >= K_NEIGHBORS_TO_CONSIDER) break; // Limit the number of neighbors
        }
    }

    // 2. Iteratively select more customers until the target number is reached.
    // This loop prioritizes selecting customers from the `current_candidates` pool,
    // which are neighbors of already selected customers, promoting connectivity.
    int consecutive_failures = 0;
    // Cap consecutive failures to prevent infinite loops if the candidate pool mostly contains
    // already selected customers (which should be rare with proper `adj` filtering).
    const int MAX_CONSECUTIVE_FAILURES = 50; 

    while (result_customers.size() < num_to_remove) {
        // If the candidate pool is empty or we've failed to pick a valid customer
        // too many times, it means the current "cluster" is exhausted or stuck.
        // In this case, pick another random unselected customer as a new seed.
        // This ensures progress and can lead to multiple disjoint removed "clusters".
        if (current_candidates.empty() || consecutive_failures >= MAX_CONSECUTIVE_FAILURES) {
            int next_seed_customer = -1;
            int search_attempts = 0;
            // Try to find an unselected customer. Limit attempts to prevent excessive loops.
            while (search_attempts < sol.instance.numCustomers * 2) { // Max attempts to find a new seed
                int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(rand_cust) == selected_customers_set.end()) {
                    next_seed_customer = rand_cust;
                    break;
                }
                search_attempts++;
            }

            if (next_seed_customer != -1) {
                selected_customers_set.insert(next_seed_customer);
                result_customers.push_back(next_seed_customer);
                
                // Add neighbors of this new seed to the candidate pool.
                neighbors_added = 0;
                for (int neighbor_node : sol.instance.adj[next_seed_customer]) {
                    if (neighbor_node == 0) continue;
                    if (selected_customers_set.find(neighbor_node) == selected_customers_set.end()) {
                        current_candidates.push_back(neighbor_node);
                        neighbors_added++;
                        if (neighbors_added >= K_NEIGHBORS_TO_CONSIDER) break;
                    }
                }
                consecutive_failures = 0; // Reset failures after successfully adding a new seed
            } else {
                // Cannot find enough unique customers to remove or all available customers are selected.
                // This scenario should be rare given the small `num_to_remove`.
                break;
            }
        }

        // If enough customers have been selected (possibly by the new seed logic), exit early.
        if (result_customers.size() == num_to_remove) break;

        // Pick a random customer from the current candidates.
        // The `getRandomNumber` uses an inclusive range.
        int rand_idx = getRandomNumber(0, (int)current_candidates.size() - 1);
        int chosen_customer = current_candidates[rand_idx];

        // Efficiently remove the chosen customer from `current_candidates` by
        // swapping it with the last element and popping.
        current_candidates[rand_idx] = current_candidates.back();
        current_candidates.pop_back();

        // Check if the chosen customer is valid (not already selected and not the depot).
        if (selected_customers_set.find(chosen_customer) == selected_customers_set.end() && chosen_customer != 0) {
            selected_customers_set.insert(chosen_customer);
            result_customers.push_back(chosen_customer);

            // Add its neighbors to the candidate pool for future selections.
            neighbors_added = 0;
            for (int neighbor_node : sol.instance.adj[chosen_customer]) {
                if (neighbor_node == 0) continue;
                if (selected_customers_set.find(neighbor_node) == selected_customers_set.end()) {
                    current_candidates.push_back(neighbor_node);
                    neighbors_added++;
                    if (neighbors_added >= K_NEIGHBORS_TO_CONSIDER) break;
                }
            }
            consecutive_failures = 0; // Reset failures after a successful selection
        } else {
            consecutive_failures++; // Increment failures if an invalid customer was picked
        }
    }
    return result_customers;
}


// Heuristic for Step 3: Customer Ordering
// This function sorts the removed customers, defining the order in which they will be
// reinserted into the solution. The sorting strategy aims to reinsert "harder" customers
// first, which can lead to more impactful solution changes. Stochasticity is added
// through a small random perturbation in the sorting key.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Define a structure to hold customer information for sorting.
    // This allows us to store multiple sorting keys and the original customer ID.
    struct CustomerSortInfo {
        int customer_id;
        float tw_slack;            // Time Window Slack: (endTW - startTW - serviceTime). Lower is tighter.
        float distance_from_depot; // Distance from depot to customer. Higher is further.
        float random_perturbation; // Small random value for stochasticity in tie-breaking.
    };

    std::vector<CustomerSortInfo> sort_data;
    sort_data.reserve(customers.size()); // Pre-allocate memory for efficiency

    // Populate the sort_data vector with information for each customer.
    for (int customer_id : customers) {
        // Calculate Time Window Slack: A measure of how much flexibility a customer's time window has.
        // A smaller slack (or negative, if not possible within TW) indicates a tighter window.
        float tw_slack = instance.endTW[customer_id] - instance.startTW[customer_id] - instance.serviceTime[customer_id];
        
        // Distance from the depot: Customers further away might be harder to fit into existing routes.
        float dist_from_depot = instance.distanceMatrix[0][customer_id];

        // Add a small random perturbation. This ensures that customers with identical primary and
        // secondary scores are sorted randomly, introducing diversity over many LNS iterations.
        // The perturbation range should be small enough not to alter the primary ordering of
        // significantly different scores.
        float rand_perturb = getRandomFraction(-0.001f, 0.001f); // Using a small float range

        sort_data.push_back({customer_id, tw_slack, dist_from_depot, rand_perturb});
    }

    // Sort the `sort_data` vector using a custom comparison lambda.
    // The sorting logic prioritizes "harder" customers first:
    // 1. Primary: Customers with tighter time windows (smaller `tw_slack`) come first.
    // 2. Secondary: If `tw_slack` is equal, customers further from the depot
    //    (larger `distance_from_depot`) come first. This can force routes to extend further.
    // 3. Tertiary: For exact ties, the random perturbation ensures a different order each time,
    //    which is crucial for stochasticity in the LNS framework.
    std::sort(sort_data.begin(), sort_data.end(), [](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        // Sort by time window slack in ascending order (tighter windows first)
        if (a.tw_slack != b.tw_slack) {
            return a.tw_slack < b.tw_slack;
        }
        // If slack is equal, sort by distance from depot in descending order (further customers first)
        if (a.distance_from_depot != b.distance_from_depot) {
            return a.distance_from_depot > b.distance_from_depot;
        }
        // For ultimate tie-breaking and stochasticity, use the random perturbation
        return a.random_perturbation < b.random_perturbation;
    });

    // Update the original `customers` vector with the newly sorted customer IDs.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data[i].customer_id;
    }
}