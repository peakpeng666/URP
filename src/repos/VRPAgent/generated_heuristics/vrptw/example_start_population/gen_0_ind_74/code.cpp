#include "AgentDesigned.h"
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_customers_vec;

    // Determine the number of customers to remove (stochastic, typically 10-30 for large instances)
    int num_to_remove = getRandomNumber(10, 30); 

    if (num_to_remove <= 0) {
        return {};
    }
    // Ensure we don't try to remove more customers than available
    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }

    // Select an initial seed customer randomly to start the removal cluster
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(seed_customer);
    selected_customers_vec.push_back(seed_customer);

    int pivot_idx_in_vec = 0; // Index to cycle through already selected customers for expansion

    // Iteratively expand the selection by adding neighbors of already selected customers
    while (selected_customers_vec.size() < num_to_remove) {
        bool expanded_this_iteration = false;
        
        // Select a pivot customer from the already selected list, cycling through them
        int current_pivot_customer = selected_customers_vec[pivot_idx_in_vec % selected_customers_vec.size()];

        // Attempt to add a neighbor of the current pivot customer
        for (int neighbor_id : sol.instance.adj[current_pivot_customer]) {
            // Check if the neighbor is a valid customer ID and not already selected
            if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers && 
                selected_set.find(neighbor_id) == selected_set.end()) {
                
                selected_set.insert(neighbor_id);
                selected_customers_vec.push_back(neighbor_id);
                expanded_this_iteration = true;
                break; // Add only one neighbor per pivot iteration to encourage broader expansion
            }
        }
        
        if (!expanded_this_iteration) {
            // If no new neighbor was added from the current_pivot_customer,
            // advance to the next pivot customer in the selected list.
            pivot_idx_in_vec++;
            
            // If all currently selected customers have been tried as pivots without success,
            // or if a pivot's adjacency list was empty/all neighbors selected,
            // pick a completely random unselected customer to diversify the search.
            if (pivot_idx_in_vec >= selected_customers_vec.size()) {
                int random_customer = getRandomNumber(1, sol.instance.numCustomers);
                int safety_counter = 0;
                const int max_safety_attempts = sol.instance.numCustomers * 2; 

                // Keep trying until an unselected random customer is found or max attempts reached
                while (selected_set.find(random_customer) != selected_set.end() && safety_counter < max_safety_attempts) {
                    random_customer = getRandomNumber(1, sol.instance.numCustomers);
                    safety_counter++;
                }

                if (safety_counter >= max_safety_attempts) {
                    break; // Could not find enough distinct customers, return what's available
                }
                
                selected_set.insert(random_customer);
                selected_customers_vec.push_back(random_customer);
                pivot_idx_in_vec = 0; // Reset pivot index to start new expansion chain from the new random customer
            }
        } else {
            // If expansion was successful, move to the next pivot in the selected list for the next iteration.
            pivot_idx_in_vec++; 
        }
    }
    return selected_customers_vec;
}

// Function to order the removed customers for reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Store pairs of (difficulty_score, customer_id)
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // Calculate a "difficulty score" for each customer based on VRPTW constraints
    // Harder-to-place customers (e.g., tight time windows, long service times) are prioritized
    for (int customer_id : customers) {
        float tw_width = instance.TW_Width[customer_id];
        float service_time = instance.serviceTime[customer_id];
        
        float score = 0.0f;

        // Component 1: Time Window Tightness
        // Smaller TW_Width means tighter window, thus higher difficulty.
        // A very small or zero width gets a large fixed score.
        if (tw_width < 1e-3f) { 
            score += 10000.0f; // Assign a very high score for extremely tight windows
        } else {
            score += 1.0f / tw_width; // Inverse relation: smaller width yields higher score
        }

        // Component 2: Service Time
        // Longer service time implies higher difficulty in fitting into tours.
        score += service_time * 10.0f; // Scale service time to give it appropriate weight

        // Component 3: Stochasticity
        // Add a small random component to introduce diversity in ordering for customers with similar scores.
        // This helps explore different reinsertion sequences.
        score += getRandomFractionFast() * 0.1f * score; // Random perturbation scaled by the current score

        customer_scores.push_back({score, customer_id});
    }

    // Sort customers based on their difficulty score in descending order (hardest first)
    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; // Sort from highest score to lowest score
              });

    // Update the input 'customers' vector with the sorted customer IDs
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}