#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle, std::min
#include <vector>    // For std::vector
#include <utility>   // For std::pair

// Include Utils.h for getRandomNumber, getRandomFractionFast etc.
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers;
    std::vector<int> candidates_for_expansion; // Customers already selected, from which we can expand

    // Determine the number of customers to remove
    // A small range (e.g., 5-25) is appropriate for large instances to keep LNS fast
    int num_to_remove = getRandomNumber(5, 25); 

    // Probability of selecting a completely new seed customer vs. expanding from an existing one
    // This adds diversity and prevents getting stuck in small local clusters
    float new_seed_prob = 0.2f; 

    // Maximum number of nearest neighbors to check for expansion
    // Limiting this keeps the search fast
    int max_neighbors_to_check = 5;

    while (selected_customers.size() < num_to_remove) {
        int current_customer_id;

        // Decide whether to pick a new random seed or expand from an existing candidate
        if (candidates_for_expansion.empty() || getRandomFractionFast() < new_seed_prob) {
            // Pick a completely new random customer as a seed (customer IDs are 1 to numCustomers)
            current_customer_id = getRandomNumber(1, sol.instance.numCustomers);
        } else {
            // Expand from an existing selected customer (a candidate for expansion)
            int rand_idx = getRandomNumber(0, candidates_for_expansion.size() - 1);
            current_customer_id = candidates_for_expansion[rand_idx];
        }

        // Try to add current_customer_id if it's new
        if (selected_customers.find(current_customer_id) == selected_customers.end()) {
            selected_customers.insert(current_customer_id);
            candidates_for_expansion.push_back(current_customer_id);
            continue; // Added a new customer, go to next iteration to check size
        }

        // If current_customer_id was already selected, try to add one of its neighbors
        bool added_neighbor = false;
        // Iterate through its nearest neighbors up to max_neighbors_to_check limit
        for (int i = 0; i < std::min((int)sol.instance.adj[current_customer_id].size(), max_neighbors_to_check); ++i) {
            int neighbor_node = sol.instance.adj[current_customer_id][i];
            if (neighbor_node == 0) continue; // Skip depot (node 0)

            // Check if the neighbor is a customer and not already selected
            if (selected_customers.find(neighbor_node) == selected_customers.end()) {
                selected_customers.insert(neighbor_node);
                candidates_for_expansion.push_back(neighbor_node);
                added_neighbor = true;
                break; // Added one neighbor, move to the next removal slot
            }
        }

        // If no new customer or neighbor was added in this iteration, 
        // the loop will continue and potentially trigger a new random seed selection
        // in the next iteration if `new_seed_prob` condition is met.
        // This implicitly handles cases where a chosen candidate has all its immediate
        // neighbors already selected or is exhausted.
    }

    return std::vector<int>(selected_customers.begin(), selected_customers.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // Calculate a score for each customer.
    // A simple score considering the profit if the customer forms a new tour.
    // Higher score means higher priority for reinsertion.
    for (int customer_id : customers) {
        float score = instance.prizes[customer_id] - (instance.distanceMatrix[0][customer_id] * 2.0f);

        // Add a small random perturbation to the score to introduce stochasticity.
        // This helps in exploring different reinsertion orders over millions of iterations.
        score += getRandomFraction(-0.01f, 0.01f) * score; 
        
        customer_scores.push_back({score, customer_id});
    }

    // Sort customers based on their calculated score in descending order.
    // Customers with higher scores will be reinserted first.
    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    // Update the input 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}