#include "AgentDesigned.h"
#include <vector>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <random>    // No direct usage of std::mt19937 or std::shuffle here, relying on Utils.h
#include <utility>   // For std::pair

// Include Utils.h to get access to random number generation functions
#include "Utils.h"

// Helper function to pick a random element from a vector.
// This is not provided in Utils.h, so it's implemented locally.
int getRandomElementFromVector(const std::vector<int>& vec) {
    if (vec.empty()) {
        return -1; // Indicate error or empty case appropriately
    }
    return vec[getRandomNumber(0, static_cast<int>(vec.size()) - 1)];
}

// Step 1: Customer selection heuristic
// Selects a subset of customers to remove based on a stochastic proximity-based expansion.
// The goal is to select customers that are generally close to each other, but not necessarily forming a single tight cluster.
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove. This range can be tuned.
    // A slightly wider range (e.g., 15-30) provides more diversity compared to 10-20 for 500+ customers.
    int num_to_remove = getRandomNumber(15, 30);

    // Use an unordered_set for efficient O(1) average-time checking of already selected customers.
    std::unordered_set<int> selected_customers_set;
    // Use a vector to maintain the list of selected customers. This allows for efficient random sampling
    // when choosing a "pivot" customer for expansion.
    std::vector<int> selected_customers_list;

    // --- Initial Seed Selection ---
    // Start by selecting a completely random customer as the first seed.
    // Customer IDs typically start from 1 (depot is 0).
    int start_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(start_customer);
    selected_customers_list.push_back(start_customer);

    // --- Iterative Expansion ---
    // Continue adding customers until the target number (`num_to_remove`) is reached.
    // This loop ensures that the selected customers tend to be spatially close, as new customers
    // are primarily selected from the neighborhood of already selected ones.
    while (selected_customers_set.size() < num_to_remove) {
        int pivot_customer;

        // Introduce stochasticity in pivot selection:
        // - With a high probability (e.g., 80%), pick a pivot from the already selected customers.
        //   This promotes the selection of spatially connected customers.
        // - With a low probability (e.g., 20%), pick a completely random customer from the entire instance.
        //   This helps to avoid getting stuck in a small, isolated cluster, and allows for starting
        //   new "mini-clusters" or bridging gaps, fulfilling the "not necessarily a single compact cluster" requirement.
        if (getRandomFractionFast() < 0.8 && !selected_customers_list.empty()) {
            pivot_customer = getRandomElementFromVector(selected_customers_list);
        } else {
            pivot_customer = getRandomNumber(1, sol.instance.numCustomers);
        }

        // Basic validation for the chosen pivot customer.
        // Depot (0) should not be selected, and a customer must have neighbors for expansion.
        if (pivot_customer == 0 || sol.instance.adj[pivot_customer].empty()) {
            continue; // Skip to the next iteration to pick another pivot
        }

        // Get the neighbors of the pivot customer. The `instance.adj` list is pre-sorted by distance,
        // so the first elements are the closest neighbors.
        const std::vector<int>& neighbors = sol.instance.adj[pivot_customer];

        // Determine how many of the closest neighbors to consider for selection.
        // This adds another layer of stochasticity: instead of always picking the absolute closest neighbor,
        // a random neighbor is chosen from a small pool of the closest ones (e.g., top 3 to 10).
        int num_neighbors_to_sample = std::min((int)neighbors.size(), getRandomNumber(3, 10));

        bool customer_added_in_this_iteration = false;
        if (num_neighbors_to_sample > 0) {
            // Randomly select one neighbor from the `num_neighbors_to_sample` closest ones.
            int candidate_idx_in_adj = getRandomNumber(0, num_neighbors_to_sample - 1);
            int candidate_customer = neighbors[candidate_idx_in_adj];

            // If the candidate is a valid customer (not depot) and not already selected, add it.
            if (candidate_customer != 0 && selected_customers_set.find(candidate_customer) == selected_customers_set.end()) {
                selected_customers_set.insert(candidate_customer);
                selected_customers_list.push_back(candidate_customer);
                customer_added_in_this_iteration = true;
            }
        }
        
        // Safeguard: If no customer was added in this iteration (e.g., all considered neighbors were
        // already selected or invalid) and we still need more customers, force a random selection.
        // This ensures the loop eventually meets the `num_to_remove` target and handles situations
        // where a selected "cluster" becomes isolated or fully consumed by the selection process.
        if (!customer_added_in_this_iteration && selected_customers_set.size() < num_to_remove) {
            int fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            // Loop to find an unselected customer if the initial random pick is already selected.
            // A safeguard counter prevents excessive looping in theoretical extreme cases.
            int safeguard_counter = 0;
            while (selected_customers_set.find(fallback_customer) != selected_customers_set.end() && safeguard_counter < sol.instance.numCustomers * 2) {
                fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
                safeguard_counter++;
            }
            // Add the fallback customer if it's new and valid.
            if (selected_customers_set.find(fallback_customer) == selected_customers_set.end() && fallback_customer != 0) {
                selected_customers_set.insert(fallback_customer);
                selected_customers_list.push_back(fallback_customer);
            }
        }
    }

    // Convert the unordered_set of selected customers into a vector for the return type.
    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}


// Step 3: Ordering of the removed customers heuristic
// Sorts the removed customers for greedy reinsertion. The order can significantly
// impact the quality of the reinsertion phase. This heuristic prioritizes "harder"
// customers based on various criteria, chosen stochastically.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return; // No customers to sort.
    }

    // A vector of pairs to store (score, customer_id). This allows sorting based on the score
    // while keeping track of the original customer ID.
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // Randomly choose one of several sorting strategies. This stochastic choice is crucial
    // for ensuring diversity over millions of LNS iterations.
    // 0: Sort by Time Window Width (tightest/narrowest time window first) - often hard to place.
    // 1: Sort by Demand (highest demand first) - consumes more vehicle capacity.
    // 2: Sort by Distance from Depot (farthest first) - potentially difficult to integrate into tours.
    int strategy = getRandomNumber(0, 2); // Selects one of the 3 strategies (0, 1, or 2).

    for (int customer_id : customers) {
        float score;
        // Add a small random noise to the score. This is vital for:
        // 1. Breaking ties between customers that have identical primary scores.
        // 2. Introducing fine-grained stochasticity, which helps explore a wider
        //    solution space over a large number of LNS iterations.
        float random_noise = getRandomFractionFast() * 0.001f; // A small, non-dominant perturbation

        if (strategy == 0) { // Strategy: Time Window Width (ascending, so narrowest first)
            // Customers with smaller time windows are generally harder to reinsert because they have fewer
            // feasible service start times. Sorting them first allows the reinsertion algorithm to prioritize
            // fitting these constrained customers.
            score = instance.TW_Width[customer_id] + random_noise;
        } else if (strategy == 1) { // Strategy: Demand (descending, so highest demand first)
            // Customers with higher demand are harder because they consume more vehicle capacity, potentially
            // limiting options for subsequent insertions. Negating the demand allows `std::sort` (which is ascending)
            // to effectively sort by demand in descending order.
            score = -instance.demand[customer_id] + random_noise;
        } else { // Strategy: Distance from Depot (descending, so farthest first)
            // Customers located far from the depot might be challenging to integrate into efficient tours,
            // as they require longer travel times. Sorting them first can force the reinsertion to consider
            // these longer segments early. Negating distance achieves descending sort.
            score = -instance.distanceMatrix[0][customer_id] + random_noise;
        }
        customer_scores.push_back({score, customer_id});
    }

    // Sort the `customer_scores` vector. `std::sort` sorts pairs based on the first element (the score)
    // in ascending order. Our score calculations (e.g., negation for descending criteria) ensure
    // the desired "hardest first" order.
    std::sort(customer_scores.begin(), customer_scores.end());

    // Update the original `customers` vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}