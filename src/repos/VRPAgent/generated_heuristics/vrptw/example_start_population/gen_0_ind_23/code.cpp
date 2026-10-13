#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort and std::swap
#include <tuple>     // For std::tuple in sort_by_llm_1

// Assume Utils.h provides getRandomNumber and getRandomFractionFast
// And AgentDesigned.h includes Solution.h, Instance.h, Tour.h

// Customer selection heuristic for the Large Neighborhood Search (LNS) framework.
// This function selects a subset of customers to remove from the current solution.
// The goal is to select customers that are "connected" or "clustered" to facilitate
// meaningful reinsertion, while incorporating stochasticity for diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;       // Stores customers already selected for removal
    std::unordered_set<int> potential_candidates_set;     // For fast lookup of customers in potential_candidates_vec
    std::vector<int> potential_candidates_vec;           // Stores customers eligible for selection, allowing random access

    // Determine the number of customers to remove. This range (10-20) provides
    // a small, controlled perturbation suitable for large instances.
    int num_to_remove = getRandomNumber(10, 20);
    // Ensure we don't try to remove more customers than available
    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }
    // Ensure at least one customer is removed if there are customers to begin with
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) {
        num_to_remove = 1;
    }

    // Step 1: Select an initial "seed" customer randomly. This customer will start a cluster.
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_seed);

    // Populate the initial potential_candidates from the neighbors of the seed customer.
    // instance.adj contains neighbors sorted by distance, so these are the closest.
    for (int neighbor_id : sol.instance.adj[initial_seed]) {
        if (neighbor_id == 0) continue; // Skip the depot (node 0)
        // Add neighbor only if not already selected and not already in the candidate pool
        if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
            potential_candidates_set.find(neighbor_id) == potential_candidates_set.end()) {
            potential_candidates_set.insert(neighbor_id);
            potential_candidates_vec.push_back(neighbor_id);
        }
    }

    // Step 2: Iteratively grow the set of selected customers until `num_to_remove` is reached.
    while (selected_customers_set.size() < num_to_remove) {
        // If the candidate pool becomes empty, it means all neighbors of currently selected
        // customers have been explored or selected. To continue, "jump" to a new random customer
        // not yet selected, effectively starting a new sub-cluster or extending the current one
        // from a new point.
        if (potential_candidates_vec.empty()) {
            int new_seed = -1;
            int attempts = 0;
            // Attempt to find a new unselected customer. Limit attempts to prevent infinite loops
            // in scenarios where most customers are already selected.
            while (attempts < sol.instance.numCustomers * 2) {
                int possible_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(possible_seed) == selected_customers_set.end()) {
                    new_seed = possible_seed;
                    break;
                }
                attempts++;
            }

            if (new_seed == -1) { // No unselected customer found after many attempts, or all customers are selected
                break; // Cannot select more customers, terminate loop
            }
            selected_customers_set.insert(new_seed); // Add the new seed

            // Add neighbors of this new seed to the candidate pool
            for (int neighbor_id : sol.instance.adj[new_seed]) {
                if (neighbor_id == 0) continue; // Skip depot
                if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                    potential_candidates_set.find(neighbor_id) == potential_candidates_set.end()) {
                    potential_candidates_set.insert(neighbor_id);
                    potential_candidates_vec.push_back(neighbor_id);
                }
            }
        }

        // After potentially re-seeding, if the candidate pool is still empty or we've reached our target, break.
        if (potential_candidates_vec.empty() || selected_customers_set.size() >= num_to_remove) {
            break;
        }

        // Pick a random customer from the `potential_candidates_vec` to add to the `selected_customers_set`.
        int idx_to_pick = getRandomNumber(0, static_cast<int>(potential_candidates_vec.size()) - 1);
        int chosen_customer = potential_candidates_vec[idx_to_pick];

        // Efficiently remove the chosen customer from both candidate tracking structures.
        std::swap(potential_candidates_vec[idx_to_pick], potential_candidates_vec.back());
        potential_candidates_vec.pop_back();
        potential_candidates_set.erase(chosen_customer);

        // Add the chosen customer to the set of selected customers.
        selected_customers_set.insert(chosen_customer);

        // Add neighbors of the newly chosen customer to the `potential_candidates_vec`
        // if they are not already selected or already in the candidate pool.
        for (int neighbor_id : sol.instance.adj[chosen_customer]) {
            if (neighbor_id == 0) continue; // Skip depot
            if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                potential_candidates_set.find(neighbor_id) == potential_candidates_set.end()) {
                potential_candidates_set.insert(neighbor_id);
                potential_candidates_vec.push_back(neighbor_id);
            }
        }
    }

    // Convert the unordered_set to a vector for the return value.
    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}


// Ordering heuristic for removed customers for greedy reinsertion.
// This function sorts the given list of `customers` (which are the ones removed
// by `select_by_llm_1`). The ordering can significantly impact the quality
// of the reinserted solution.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers based on a composite score:
    // 1. Primary criterion: Time Window Width (smaller width indicates a tighter/harder time window).
    // 2. Secondary criterion: Service Time (longer service time might indicate a harder customer).
    // Stochasticity is added to both criteria to ensure diversity over many iterations.
    std::vector<std::tuple<float, float, int>> customer_sort_data; // Tuple: {effective_tw_width, effective_service_time_negated, customer_id}
    customer_sort_data.reserve(customers.size());

    // Small perturbation scales for stochasticity. These values can be tuned.
    // They are small enough not to drastically change the primary sort order,
    // but large enough to break ties randomly and introduce diversity.
    const float RANDOM_PERTURBATION_SCALE_TW = 0.001f;
    const float RANDOM_PERTURBATION_SCALE_ST = 0.0001f;

    for (int customer_id : customers) {
        // Calculate an "effective" time window width.
        // A smaller value means tighter window, which we want to prioritize (sort first).
        float effective_tw_width = instance.TW_Width[customer_id] +
                                   (getRandomFractionFast() * RANDOM_PERTURBATION_SCALE_TW);

        // Calculate an "effective" service time, negated.
        // We want to prioritize customers with longer service times among those with similar TW_Widths.
        // By negating, we can use std::sort's default ascending order to achieve descending sort on service time.
        float effective_service_time_negated = - (instance.serviceTime[customer_id] +
                                                  (getRandomFractionFast() * RANDOM_PERTURBATION_SCALE_ST));

        customer_sort_data.emplace_back(effective_tw_width, effective_service_time_negated, customer_id);
    }

    // Sort the customers based on the tuples. std::tuple sorts lexicographically:
    // 1. By `effective_tw_width` in ascending order (tighter time windows come first).
    // 2. Then by `effective_service_time_negated` in ascending order, which effectively
    //    sorts by `serviceTime` in descending order (longer service times come first for ties in TW_Width).
    std::sort(customer_sort_data.begin(), customer_sort_data.end());

    // Update the original `customers` vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = std::get<2>(customer_sort_data[i]);
    }
}