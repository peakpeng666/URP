#include "AgentDesigned.h" // Assumed to include Solution.h, Instance.h, Tour.h, Utils.h
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort
#include <vector>
#include <utility>   // For std::pair

// Using static thread_local for random number generation for performance and thread safety.
// These are initialized once per thread.
static thread_local std::mt19937 random_gen(std::random_device{}());

// Helper function to get a random float for internal use in these heuristics.
// Utilizes getRandomFractionFast() from Utils.h for speed.
float get_random_float_0_1() {
    return getRandomFractionFast();
}

// Customer selection heuristic for LNS (Step 1)
// Selects a subset of customers to remove based on proximity and stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    // `candidates_for_expansion` stores customers already selected, from which new customers can be chosen
    // It's effectively a queue for BFS-like expansion, but we pick randomly from it for stochasticity.
    std::vector<int> candidates_for_expansion;

    // Determine the number of customers to remove.
    // The range (10-25) balances removal size with LNS iteration speed and impact.
    int num_to_remove = getRandomNumber(10, 25);
    
    // Handle edge cases for very small instances or if no customers exist.
    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }
    // Ensure at least one customer is selected if possible and num_to_remove was 0
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) {
        num_to_remove = 1;
    }

    // Step 1: Select an initial seed customer.
    // Customer IDs are typically 1-based, 0 being the depot.
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(initial_seed);
    candidates_for_expansion.push_back(initial_seed);

    size_t current_candidate_idx = 0; // Index for iterating through candidates_for_expansion

    // Step 2: Expand from selected customers until the target number is reached.
    while (selected_set.size() < num_to_remove) {
        // If all current candidates have been explored or exhausted,
        // add a new random seed to ensure `num_to_remove` is met and to create
        // potentially disconnected components of removed customers.
        // The condition `current_candidate_idx >= candidates_for_expansion.size()` means we've tried all existing candidates.
        // The `num_to_remove * 2` limit is a heuristic to prevent over-exploring tiny clusters and force new seeds faster.
        if (current_candidate_idx >= candidates_for_expansion.size() || current_candidate_idx > num_to_remove * 2) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            // Attempt to find a new seed that is not already in the selected set.
            int attempt_count = 0;
            const int max_seed_attempts = 100;
            while (selected_set.count(new_seed) && attempt_count < max_seed_attempts) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                attempt_count++;
            }
            // If after max_seed_attempts, we still can't find a unique seed, it implies most customers are already selected.
            if (selected_set.count(new_seed) && selected_set.size() < num_to_remove) {
                // If we absolutely can't find a new seed and haven't hit the target,
                // it might be due to a very small instance where all customers are already picked.
                // In this rare case, just break to return what we have.
                break; 
            }
            
            selected_set.insert(new_seed);
            candidates_for_expansion.push_back(new_seed);
            // Reset index to start exploring from the newly added seed.
            current_candidate_idx = candidates_for_expansion.size() - 1; 

            if (selected_set.size() == num_to_remove) {
                break; // Target reached
            }
        }

        int current_customer_to_expand = candidates_for_expansion[current_candidate_idx];

        // Shuffle the neighbors of the current customer to introduce stochasticity in selection order.
        std::vector<int> neighbors = sol.instance.adj[current_customer_to_expand];
        std::shuffle(neighbors.begin(), neighbors.end(), random_gen);

        bool added_any_neighbor_in_this_step = false;
        for (int neighbor_id : neighbors) {
            // Ensure the neighbor is a valid customer ID (1 to numCustomers).
            if (neighbor_id == 0 || neighbor_id > sol.instance.numCustomers) {
                continue; // Skip depot or invalid IDs
            }

            // Introduce stochasticity: only consider adding a neighbor with a certain probability (e.g., 60%).
            // This prevents always picking all neighbors and diversifies the removed set's shape.
            if (get_random_float_0_1() < 0.6) {
                continue;
            }

            // If the neighbor is not already selected, add it to the set and to candidates for future expansion.
            if (selected_set.find(neighbor_id) == selected_set.end()) {
                selected_set.insert(neighbor_id);
                candidates_for_expansion.push_back(neighbor_id);
                added_any_neighbor_in_this_step = true;
                if (selected_set.size() == num_to_remove) {
                    break; // Target reached
                }
            }
        }

        // If no new neighbors were added from the current customer, move to the next candidate.
        // This ensures progress if a customer has no unselected neighbors, or if stochasticity prevented adding them.
        if (!added_any_neighbor_in_this_step) {
            current_candidate_idx++;
        }
        // If neighbors were added, we might still want to expand from the current customer (if there are more neighbors to explore
        // or if the stochastic choice was to not add all neighbors).
        // For simplicity and to ensure progress, we always increment current_candidate_idx here,
        // which effectively makes it a breadth-first-like expansion where we try each current candidate once,
        // then move to the next. The `candidates_for_expansion` grows, ensuring we don't get stuck.
        else {
             current_candidate_idx++;
        }
    }

    return std::vector<int>(selected_set.begin(), selected_set.end());
}


// Ordering heuristic for removed customers (Step 3)
// Sorts the given customers based on a stochastically chosen criterion and order,
// applying a minor perturbation for diversity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Stochastically choose a sorting strategy:
    // 0: Pure random shuffle (baseline)
    // 1: Sort by customer demand
    // 2: Sort by distance to depot
    int strategy_choice = getRandomNumber(0, 2); 
    
    // Stochastically choose sorting order: true for ascending, false for descending.
    bool sort_ascending = (get_random_float_0_1() < 0.5); 

    if (strategy_choice == 0) {
        // Strategy 0: Pure random shuffle. This is fast and provides maximum diversity in order.
        std::shuffle(customers.begin(), customers.end(), random_gen);
    } else {
        // Strategies 1 and 2: Feature-based sorting.
        // Create pairs of (value, customer_id) to sort based on the value.
        std::vector<std::pair<float, int>> customer_values;
        customer_values.reserve(customers.size());

        if (strategy_choice == 1) {
            // Strategy 1: Sort by customer demand.
            for (int customer_id : customers) {
                customer_values.push_back({static_cast<float>(instance.demand[customer_id]), customer_id});
            }
        } else { // strategy_choice == 2
            // Strategy 2: Sort by distance to depot (node 0).
            for (int customer_id : customers) {
                customer_values.push_back({instance.distanceMatrix[0][customer_id], customer_id});
            }
        }

        // Apply sorting based on chosen criteria and order.
        if (sort_ascending) {
            std::sort(customer_values.begin(), customer_values.end());
        } else {
            // Use reverse iterators for descending order.
            std::sort(customer_values.rbegin(), customer_values.rend());
        }

        // Extract the sorted customer IDs back into the original vector.
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_values[i].second;
        }

        // Apply a stochastic perturbation to the sorted list.
        // This prevents the sorting from being entirely deterministic and adds more diversity
        // to the reinsertion process without significantly altering the primary order.
        // Swapping adjacent elements with a small probability (e.g., 15%).
        float swap_probability = 0.15; 
        for (size_t i = 0; i + 1 < customers.size(); ++i) {
            if (get_random_float_0_1() < swap_probability) {
                std::swap(customers[i], customers[i+1]);
            }
        }
    }
}