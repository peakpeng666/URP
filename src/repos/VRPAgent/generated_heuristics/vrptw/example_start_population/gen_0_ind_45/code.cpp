#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort, std::shuffle, std::min

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // Determine the number of customers to remove. A small, stochastic number.
    // This value can be tuned based on problem size and desired search intensity.
    int numCustomersToRemove = getRandomNumber(5, 25); 

    // `candidate_pool_vec` stores potential customers to be added next.
    // These are typically geographical neighbors of already selected customers.
    // It's a vector to allow shuffling for stochastic selection.
    std::vector<int> candidate_pool_vec; 

    // Helper lambda to add a customer to `selectedCustomers` and populate `candidate_pool_vec` with its neighbors.
    // This ensures that the removal process tends to select spatially close customers.
    auto add_customer_and_update_pool = [&](int customer_id) {
        // Only add if not already selected
        if (selectedCustomers.find(customer_id) == selectedCustomers.end()) {
            selectedCustomers.insert(customer_id);
            
            // Add the closest neighbors of the newly selected customer to the candidate pool.
            // Using `instance.adj` which is pre-sorted by distance, so first few are closest.
            int num_neighbors_to_consider = std::min((int)sol.instance.adj[customer_id].size(), 10); // Consider up to 10 closest neighbors
            for (int i = 0; i < num_neighbors_to_consider; ++i) {
                int neighbor_id = sol.instance.adj[customer_id][i];
                // Only add neighbor to pool if it's not already selected.
                // We don't worry about duplicates within `candidate_pool_vec` itself as `std::shuffle`
                // and subsequent `selectedCustomers.find` check handle them efficiently.
                if (selectedCustomers.find(neighbor_id) == selectedCustomers.end()) { 
                    candidate_pool_vec.push_back(neighbor_id);
                }
            }
        }
    };

    // Step 1: Select the initial seed customer.
    // We try to pick a random customer from an existing tour to encourage "patch" removals
    // related to current solution structure.
    int initial_seed_customer = -1;
    if (!sol.tours.empty()) {
        int random_tour_idx = getRandomNumber(0, sol.tours.size() - 1);
        const Tour& tour = sol.tours[random_tour_idx];
        if (!tour.customers.empty()) {
            initial_seed_customer = tour.customers[getRandomNumber(0, tour.customers.size() - 1)];
        }
    }
    // Fallback: if no tours or tours are empty (e.g., in very early stages or edge cases),
    // pick a completely random customer.
    if (initial_seed_customer == -1) { 
        initial_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    }
    add_customer_and_update_pool(initial_seed_customer);

    // Step 2: Iteratively add more customers until `numCustomersToRemove` is reached.
    while (selectedCustomers.size() < numCustomersToRemove) {
        int next_customer_to_add = -1;

        // Option A: Prioritize selecting from the `candidate_pool_vec`.
        // This promotes the "close to at least one other selected customer" requirement.
        // We use a high probability (e.g., 85%) to favor neighborhood growth.
        if (!candidate_pool_vec.empty() && getRandomFractionFast() < 0.85) { 
            // Shuffle the candidate pool to ensure randomness in neighbor selection,
            // even if new neighbors are added at the end of the vector.
            static thread_local std::mt19937 gen_select(std::random_device{}()); // Use a local generator for shuffle
            std::shuffle(candidate_pool_vec.begin(), candidate_pool_vec.end(), gen_select);
            
            // Iterate through the shuffled candidates to find the first one not yet selected.
            for (int candidate_id : candidate_pool_vec) {
                if (selectedCustomers.find(candidate_id) == selectedCustomers.end()) {
                    next_customer_to_add = candidate_id;
                    break; 
                }
            }
        } 
        
        // Option B: Fallback to picking a completely random unselected customer.
        // This ensures diversity, allows starting new "patches" of removed customers,
        // and prevents the process from getting stuck if a local cluster of neighbors is exhausted.
        if (next_customer_to_add == -1) {
            // Efficiently find a random unselected customer by retrying random picks.
            // Limiting retries to a reasonable number (e.g., 100 or `numCustomersToRemove` * 4)
            // to prevent very long loops for very sparse solutions.
            for (int retry_count = 0; retry_count < std::min(sol.instance.numCustomers, 100); ++retry_count) { 
                int random_customer_id = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(random_customer_id) == selectedCustomers.end()) {
                    next_customer_to_add = random_customer_id;
                    break;
                }
            }
            // If many retries fail (e.g., very few customers left to select),
            // iterate linearly through all customers as a final safeguard.
            if (next_customer_to_add == -1) { 
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (selectedCustomers.find(i) == selectedCustomers.end()) {
                        next_customer_to_add = i;
                        break;
                    }
                }
            }
        }
        
        // If a customer was successfully identified, add it and update the candidate pool.
        if (next_customer_to_add != -1) {
            add_customer_and_update_pool(next_customer_to_add);
        } else {
            // This case should ideally only happen if numCustomersToRemove is greater than total customers,
            // or if all customers are already selected, which is unlikely given the small removal count.
            break; 
        }
    }
    
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // This heuristic sorts the removed customers before reinsertion.
    // A common strategy for greedy reinsertion is to prioritize customers
    // that are "harder to place" first. This ensures they find a feasible spot
    // before easier-to-place customers fill up the most convenient locations.

    // Criteria for "difficulty" or "priority":
    // 1. Time Window Width: Customers with tighter time windows (smaller TW_Width)
    //    are generally harder to place. Sort in ascending order of TW_Width.
    // 2. Service Time: Customers requiring longer service times might be harder
    //    due to accumulating time. Sort in descending order of serviceTime.
    // 3. Demand: Customers with higher demand might be harder due to vehicle capacity
    //    constraints. Sort in descending order of demand.
    // 4. Stochasticity: Add a small random perturbation to the primary sort key
    //    to break ties and introduce diversity over millions of LNS iterations.
    //    This prevents the algorithm from always reinserting identical customer sets
    //    in the exact same order when their characteristics are very similar.

    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        // Retrieve relevant instance data for comparison
        float tw_width1 = instance.TW_Width[c1];
        float service_time1 = instance.serviceTime[c1];
        int demand1 = instance.demand[c1];

        float tw_width2 = instance.TW_Width[c2];
        float service_time2 = instance.serviceTime[c2];
        int demand2 = instance.demand[c2];

        // Add a small random noise to Time Window Width for stochastic tie-breaking.
        // The noise is small (e.g., 1e-4) to ensure it only affects customers
        // with very similar time window widths and doesn't disrupt the main sorting logic.
        float noise1 = getRandomFractionFast() * 1e-4; 
        float noise2 = getRandomFractionFast() * 1e-4;

        // Primary sort key: Time Window Width (ascending, tighter windows first)
        if ((tw_width1 + noise1) != (tw_width2 + noise2)) {
            return (tw_width1 + noise1) < (tw_width2 + noise2);
        }

        // Secondary sort key: Service Time (descending, longer service times first)
        if (service_time1 != service_time2) {
            return service_time1 > service_time2;
        }

        // Tertiary sort key: Demand (descending, higher demand first)
        if (demand1 != demand2) {
            return demand1 > demand2;
        }

        // If all specified characteristics (even with noise) are identical,
        // their relative order is maintained by `std::sort` (stable sort).
        return false; 
    });
}