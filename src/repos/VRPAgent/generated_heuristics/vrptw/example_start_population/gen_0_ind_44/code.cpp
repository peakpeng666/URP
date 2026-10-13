#include "AgentDesigned.h" // Assuming this includes Solution.h, Tour.h, Instance.h
#include <unordered_set>    // For fast lookup of selected customers
#include <vector>           // For dynamic arrays
#include <algorithm>        // For std::sort
#include "Utils.h"          // For getRandomNumber, getRandomFraction

// Heuristic for Step 1: Customer Selection
// Selects a subset of customers to remove based on a "relatedness" criterion (geographical proximity).
// This is a variant of the "Shaw removal" or "related removal" operator.
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove, within a specified range.
    // For 500+ customers, removing 4-8% seems reasonable for a destroy operator.
    int numCustomersToRemove = getRandomNumber(20, 40); 

    // Use a vector to maintain the order of selection if needed (e.g., for specific destroy logic),
    // and an unordered_set for fast checking if a customer is already selected.
    std::vector<int> removed_customers_list; 
    std::unordered_set<int> removed_customers_set; 

    // 1. Pick a random customer as the initial seed for removal.
    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    removed_customers_list.push_back(initial_customer_id);
    removed_customers_set.insert(initial_customer_id);

    // 2. Iteratively add customers that are geographically close to already selected ones.
    // This process encourages the removal of a "cluster" or "group" of related customers.
    while (removed_customers_list.size() < numCustomersToRemove) {
        // Select a random customer from the already selected ones as a "pivot".
        // Expanding from any previously selected customer helps explore different directions.
        int pivot_idx = getRandomNumber(0, (int)removed_customers_list.size() - 1);
        int pivot_customer_id = removed_customers_list[pivot_idx];

        bool added_customer_this_iteration = false;

        // Iterate through the neighbors of the pivot customer.
        // `sol.instance.adj` is expected to be sorted by distance, so closer neighbors appear first.
        for (int neighbor_id : sol.instance.adj[pivot_customer_id]) {
            // Ensure the neighbor_id refers to a valid customer (not depot and within bounds)
            // and that it has not been selected for removal already.
            if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers &&
                removed_customers_set.find(neighbor_id) == removed_customers_set.end()) {
                
                removed_customers_list.push_back(neighbor_id);
                removed_customers_set.insert(neighbor_id);
                added_customer_this_iteration = true;
                break; // Found and added one related customer, move to the next removal slot.
            }
        }

        // Fallback mechanism: If no suitable (unselected) neighbor was found for the current pivot
        // (e.g., all its closest neighbors are already selected, or it has no customers as neighbors),
        // then pick a completely random unselected customer. This prevents getting stuck and ensures
        // the target number of customers is reached, while still introducing diversity.
        if (!added_customer_this_iteration) {
            int random_unselected_customer = -1;
            // Iterate a few times to find an unselected customer; handles unlikely edge cases.
            for (int attempt = 0; attempt < sol.instance.numCustomers * 2; ++attempt) {
                int candidate_customer_id = getRandomNumber(1, sol.instance.numCustomers);
                if (removed_customers_set.find(candidate_customer_id) == removed_customers_set.end()) {
                    random_unselected_customer = candidate_customer_id;
                    break;
                }
            }
            
            if (random_unselected_customer != -1) {
                removed_customers_list.push_back(random_unselected_customer);
                removed_customers_set.insert(random_unselected_customer);
            } else {
                // This scenario is highly unlikely for typical VRPTW problem sizes,
                // meaning we couldn't find enough distinct customers to remove.
                break; 
            }
        }
    }

    return removed_customers_list;
}

// Heuristic for Step 3: Ordering of Removed Customers
// Sorts the removed customers based on their "difficulty" for reinsertion, with stochasticity.
// Harder customers (e.g., tight time windows) are typically reinserted first.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // To introduce stochasticity and ensure a stable sort key for the comparator,
    // we create temporary `CustomerSortInfo` objects for each customer.
    struct CustomerSortInfo {
        int id;             // Original customer ID
        float effective_tw_width; // Time window width with added random perturbation
        int demand;         // Customer's demand
        float service_time; // Customer's service time
    };

    std::vector<CustomerSortInfo> sort_data;
    sort_data.reserve(customers.size()); // Pre-allocate memory for efficiency

    // Scale for adding random perturbation to the time window width.
    // This small noise helps to randomize the order of customers with very similar (or identical)
    // time window widths, ensuring diversity across millions of LNS iterations.
    const float TW_PERTURB_SCALE = 0.5f; 

    // Populate `sort_data` with customer information and a unique perturbed time window width.
    for (int customer_id : customers) {
        sort_data.push_back({
            customer_id,
            instance.TW_Width[customer_id] + getRandomFraction(-TW_PERTURB_SCALE, TW_PERTURB_SCALE),
            instance.demand[customer_id],
            instance.serviceTime[customer_id]
        });
    }

    // Sort the `sort_data` vector using a custom comparison lambda function.
    std::sort(sort_data.begin(), sort_data.end(), [](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        // Primary sort key: Effective Time Window Width (ascending).
        // Customers with tighter time windows (smaller `effective_tw_width`) are harder to place
        // and should be reinserted first.
        if (a.effective_tw_width != b.effective_tw_width) {
            return a.effective_tw_width < b.effective_tw_width;
        }

        // Secondary sort key: Demand (descending).
        // If time window widths are effectively equal, customers with higher demand are harder
        // to fit and should be reinserted next.
        if (a.demand != b.demand) {
            return a.demand > b.demand;
        }

        // Tertiary sort key: Service Time (descending).
        // If both time window widths and demands are equal, customers with longer service times
        // are harder to accommodate and are prioritized.
        return a.service_time > b.service_time;
    });

    // Update the original `customers` vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data[i].id;
    }
}