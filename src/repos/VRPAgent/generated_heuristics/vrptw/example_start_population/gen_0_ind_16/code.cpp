#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::shuffle, std::find, std::min
#include <numeric>   // Not directly used but often helpful

#include "Utils.h" // For getRandomNumber, getRandomFractionFast, argsort

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove.
    // This provides stochasticity in the scale of removal and handles large instances.
    int num_to_remove = getRandomNumber(10, 30); // Aim for 10-30 customers removed
    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }

    std::unordered_set<int> selected_customers_set;
    std::vector<int> expansion_candidates_queue; // Customers whose neighbors we will consider for removal

    // 1. Initial Seed Selection: Pick a random customer to start the removal process.
    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_customer_id);
    expansion_candidates_queue.push_back(initial_customer_id);

    // 2. Iterative Expansion: Grow the set of removed customers by selecting neighbors of already removed customers.
    while (selected_customers_set.size() < num_to_remove) {
        if (expansion_candidates_queue.empty()) {
            // Fallback: If no more connected customers to expand from, pick a truly random unselected customer.
            // This ensures we reach `num_to_remove` even if the initial cluster is small or exhausted.
            int fallback_customer = -1;
            int num_attempts = 0;
            const int MAX_ATTEMPTS = 100; // Limit attempts to prevent infinite loops in rare edge cases
            while (num_attempts < MAX_ATTEMPTS) {
                int random_unselected = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(random_unselected) == selected_customers_set.end()) {
                    fallback_customer = random_unselected;
                    break;
                }
                num_attempts++;
            }

            if (fallback_customer != -1) {
                selected_customers_set.insert(fallback_customer);
                expansion_candidates_queue.push_back(fallback_customer);
            } else {
                // If we can't find any more unselected customers, break the loop.
                // This shouldn't happen for 500+ customers with small `num_to_remove`.
                break;
            }
        }

        // Pick a random customer from the expansion candidates queue.
        int queue_idx = getRandomNumber(0, expansion_candidates_queue.size() - 1);
        int current_pivot_customer = expansion_candidates_queue[queue_idx];

        // Remove the chosen pivot from the queue to prevent re-processing it as a primary pivot too frequently.
        std::swap(expansion_candidates_queue[queue_idx], expansion_candidates_queue.back());
        expansion_candidates_queue.pop_back();

        std::vector<int> potential_new_removals;

        // Add geographic neighbors: Consider a small number of closest neighbors from `adj`.
        int num_geo_neighbors_to_consider = std::min((int)sol.instance.adj[current_pivot_customer].size(), 5); // Limit to 5 closest
        for (int i = 0; i < num_geo_neighbors_to_consider; ++i) {
            potential_new_removals.push_back(sol.instance.adj[current_pivot_customer][i]);
        }

        // Add tour neighbors: Consider predecessor and successor in the current tour.
        int tour_idx = sol.customerToTourMap[current_pivot_customer];
        // Check if tour_idx is valid (can be -1 or out of bounds if customer not assigned to a tour, though problem implies all served)
        if (tour_idx >= 0 && tour_idx < sol.tours.size()) {
            const Tour& tour = sol.tours[tour_idx];
            if (tour.customers.size() > 1) { // A customer needs at least one other customer in its tour to have tour neighbors
                // Find the position of the current_pivot_customer in its tour.
                // Using std::find is O(N) where N is tour length, which is acceptable for single tour.
                auto it = std::find(tour.customers.begin(), tour.customers.end(), current_pivot_customer);
                if (it != tour.customers.end()) {
                    int customer_pos = std::distance(tour.customers.begin(), it);
                    if (customer_pos > 0) {
                        potential_new_removals.push_back(tour.customers[customer_pos - 1]); // Predecessor
                    }
                    if (customer_pos < tour.customers.size() - 1) {
                        potential_new_removals.push_back(tour.customers[customer_pos + 1]); // Successor
                    }
                }
            }
        }

        // Stochastically select one neighbor to add to `selected_customers_set`.
        // Shuffle the potential_new_removals to introduce more randomness in selection.
        // Using a thread_local random generator for performance.
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(potential_new_removals.begin(), potential_new_removals.end(), gen);
        
        bool added_a_neighbor = false;
        for (int neighbor_id : potential_new_removals) {
            if (selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                selected_customers_set.insert(neighbor_id);
                expansion_candidates_queue.push_back(neighbor_id); // Newly selected customer also becomes an expansion candidate
                added_a_neighbor = true;
                break; // Only add one new neighbor per pivot to control growth speed and allow other pivots to be chosen.
            }
        }
    }

    // Convert the set of selected customers to a vector.
    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<float> difficulty_scores(customers.size());
    for (size_t i = 0; i < customers.size(); ++i) {
        int customer_id = customers[i];
        float score = 0.0f;

        // Factor 1: Time Window Width (smaller width = harder to place = higher difficulty score)
        // Add 1.0f to denominator to avoid division by zero if TW_Width is 0.
        score += 1000.0f / (instance.TW_Width[customer_id] + 1.0f); 
        
        // Factor 2: Start Time Window (earlier start = harder to fit = higher difficulty score)
        // Similar to TW_Width, smaller startTW means higher score. Max startTW could be large.
        score += 100.0f / (instance.startTW[customer_id] + 1.0f); 

        // Factor 3: Demand (higher demand = harder to fit = higher difficulty score)
        // Normalize by vehicle capacity and scale up.
        score += (float)instance.demand[customer_id] / instance.vehicleCapacity * 10.0f; 

        // Stochastic component: Add small random noise to break ties and introduce diversity.
        score += getRandomFractionFast() * 0.1f; 

        difficulty_scores[i] = score;
    }

    // Use argsort to get indices that would sort `difficulty_scores` in ascending order.
    // Since we want "harder" customers (higher difficulty scores) to be reinserted first,
    // we need to sort the `customers` vector in descending order of `difficulty_scores`.
    // By providing argsort with negated scores, it effectively sorts in descending order of original scores.
    
    std::vector<float> negated_scores(difficulty_scores.size());
    for(size_t i = 0; i < difficulty_scores.size(); ++i) {
        negated_scores[i] = -difficulty_scores[i];
    }

    std::vector<int> sorted_indices = argsort(negated_scores);

    // Reorder the original 'customers' vector according to the sorted indices.
    std::vector<int> reordered_customers(customers.size());
    for (size_t i = 0; i < customers.size(); ++i) {
        reordered_customers[i] = customers[sorted_indices[i]];
    }
    customers = reordered_customers;
}