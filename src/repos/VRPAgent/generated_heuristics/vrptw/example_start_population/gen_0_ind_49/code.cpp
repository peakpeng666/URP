#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle
#include <vector>    // For std::vector
#include <utility>   // For std::pair

// Include Utils.h for random number generation functions
#include "Utils.h"

// Helper function to safely get a random number within a thread_local context
// This is already provided by getRandomNumber, getRandomFraction, getRandomFractionFast in Utils.h
// so no need to redefine std::mt19937 here.

// select_by_llm_1: Customer selection heuristic
// Selects a subset of customers to remove based on a "growing cluster" approach
// ensuring selected customers are close to each other while incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove, with some randomness
    int num_to_remove = getRandomNumber(15, 30); // A small range for large instances

    std::vector<int> selected_customers_list;
    std::unordered_set<int> selected_customers_set; // For fast O(1) lookups

    std::vector<int> frontier_customers_list; // Customers that are neighbors of selected ones, not yet selected
    std::unordered_set<int> frontier_customers_set; // For fast O(1) lookups if a customer is already in frontier_customers_list

    // 1. Pick a random seed customer to start the "cluster"
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers); // Customer IDs are 1-based

    selected_customers_list.push_back(seed_customer);
    selected_customers_set.insert(seed_customer);

    // 2. Populate the initial frontier with neighbors of the seed customer
    // Limit the number of neighbors considered to keep the frontier manageable and fast
    const int max_neighbors_to_consider = 15; 
    
    int current_neighbors_count = 0;
    for (int neighbor_id : sol.instance.adj[seed_customer]) {
        if (current_neighbors_count >= max_neighbors_to_consider) break; // Limit processing
        
        // Ensure neighbor is a valid customer (not depot 0) and not already selected or in the frontier
        if (neighbor_id != 0 &&
            selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
            frontier_customers_set.find(neighbor_id) == frontier_customers_set.end()) {
            
            frontier_customers_list.push_back(neighbor_id);
            frontier_customers_set.insert(neighbor_id);
        }
        current_neighbors_count++;
    }

    // 3. Iteratively add customers from the frontier until target count is reached
    while (selected_customers_list.size() < num_to_remove) {
        if (frontier_customers_list.empty()) {
            // Fallback: If the frontier is empty (e.g., all neighbors already selected or no more neighbors),
            // pick a completely random unselected customer as a new seed.
            int fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            while (selected_customers_set.count(fallback_customer) || fallback_customer == 0) {
                fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            }
            
            selected_customers_list.push_back(fallback_customer);
            selected_customers_set.insert(fallback_customer);

            // Add its neighbors to the frontier
            current_neighbors_count = 0;
            for (int neighbor_id : sol.instance.adj[fallback_customer]) {
                if (current_neighbors_count >= max_neighbors_to_consider) break;

                if (neighbor_id != 0 &&
                    selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                    frontier_customers_set.find(neighbor_id) == frontier_customers_set.end()) {
                    
                    frontier_customers_list.push_back(neighbor_id);
                    frontier_customers_set.insert(neighbor_id);
                }
                current_neighbors_count++;
            }
            continue; // Go to next iteration to check size
        }

        // Pick a random customer from the frontier to add
        int picked_idx = getRandomNumber(0, (int)frontier_customers_list.size() - 1);
        int current_customer = frontier_customers_list[picked_idx];

        // Remove the picked customer from the frontier lists
        // Swap with last and pop_back for O(1) removal from vector (order doesn't matter)
        frontier_customers_list[picked_idx] = frontier_customers_list.back();
        frontier_customers_list.pop_back();
        frontier_customers_set.erase(current_customer);

        // This check should ideally not be needed if logic is perfect, but good for safety
        if (selected_customers_set.count(current_customer)) {
            continue; // Already selected, pick another one
        }

        // Add the current customer to the selected set
        selected_customers_list.push_back(current_customer);
        selected_customers_set.insert(current_customer);

        // Add its unselected and un-frontiervized neighbors to the frontier
        current_neighbors_count = 0;
        for (int neighbor_id : sol.instance.adj[current_customer]) {
            if (current_neighbors_count >= max_neighbors_to_consider) break;

            if (neighbor_id != 0 &&
                selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                frontier_customers_set.find(neighbor_id) == frontier_customers_set.end()) {
                
                frontier_customers_list.push_back(neighbor_id);
                frontier_customers_set.insert(neighbor_id);
            }
            current_neighbors_count++;
        }
    }

    return selected_customers_list;
}

// sort_by_llm_1: Ordering of the removed customers for reinsertion
// Sorts customers based on a 'difficulty' score, incorporating stochastic noise.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Create a vector of pairs to store (difficulty_score, customer_id)
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size()); // Pre-allocate memory

    // Calculate a "difficulty" score for each customer
    for (int customer_id : customers) {
        float score = 0.0;

        // Factor 1: Distance from depot (further is generally harder to fit within time windows)
        score += instance.distanceMatrix[0][customer_id];

        // Factor 2: Demand (larger demand reduces vehicle capacity more, harder to fit)
        // Scaled by 5.0 to give it more weight relative to distance (e.g., demand 100 -> score 500)
        score += instance.demand[customer_id] * 5.0f;

        // Factor 3: Service Time (longer service time reduces flexibility)
        // Scaled by 10.0 (e.g., service time 30 -> score 300)
        score += instance.serviceTime[customer_id] * 10.0f;

        // Factor 4: Time Window Width (tighter time windows are harder to satisfy)
        // Use 1.0 / (width + epsilon) to ensure smaller width gives higher score.
        // Scaled by 50.0 (e.g., width 1 -> score ~500)
        // Add a small constant to prevent division by zero for extremely small or zero TW_Width
        score += (1.0f / (instance.TW_Width[customer_id] + 0.1f)) * 50.0f;

        // Introduce stochastic noise to ensure diversity over millions of iterations.
        // This will slightly perturb the order, breaking ties and exploring variations.
        // Noise factor of 10.0 means random perturbation between 0 and 10.
        score += getRandomFractionFast() * 10.0f; 

        customer_scores.push_back({score, customer_id});
    }

    // Sort customers based on their calculated scores in descending order
    // (Higher score means "harder" or more constrained, so reinsert first)
    std::sort(customer_scores.rbegin(), customer_scores.rend());

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}