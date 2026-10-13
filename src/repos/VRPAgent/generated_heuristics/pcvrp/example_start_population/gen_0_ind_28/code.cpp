#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove.
    // A small percentage (e.g., 3-7%) for 500 customers results in 15-35 removals.
    int num_to_remove = getRandomNumber(15, 35); 
    if (num_to_remove > sol.instance.numCustomers) { 
        num_to_remove = sol.instance.numCustomers; // Cap at total number of customers
    }
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) { // Ensure at least one customer is removed if possible
        num_to_remove = 1;
    } else if (sol.instance.numCustomers == 0) { // No customers to remove
        return {};
    }

    std::unordered_set<int> selected_customers_set;
    
    // Seed the selection with an initial customer.
    // Prioritize visited customers (if any) to encourage structural changes in existing tours,
    // but also allow selecting unvisited customers to give them a chance for reinsertion.
    int start_customer;
    bool found_visited = false;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            found_visited = true;
            break;
        }
    }

    if (found_visited && getRandomFractionFast() < 0.8) { // 80% chance to start with a visited customer
        std::vector<int> visited_customers_ids;
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (sol.customerToTourMap[i] != -1) {
                visited_customers_ids.push_back(i);
            }
        }
        start_customer = visited_customers_ids[getRandomNumber(0, visited_customers_ids.size() - 1)];
    } else {
        start_customer = getRandomNumber(1, sol.instance.numCustomers); // Pick any customer (visited or unvisited)
    }
    selected_customers_set.insert(start_customer);

    // Iteratively expand the selection by choosing neighbors of already selected customers.
    // This encourages selecting customers that are geographically close to each other.
    while (selected_customers_set.size() < num_to_remove) {
        bool candidate_found = false;
        int num_tries = 0;
        const int MAX_EXPANSION_TRIES = 50; // Limit attempts to find a suitable neighbor

        while (!candidate_found && num_tries < MAX_EXPANSION_TRIES) {
            // Pick a random customer from the set of already selected customers to expand from.
            int random_idx_in_set = getRandomNumber(0, selected_customers_set.size() - 1);
            auto it = selected_customers_set.begin();
            std::advance(it, random_idx_in_set);
            int source_customer = *it;

            const std::vector<int>& neighbors = sol.instance.adj[source_customer];
            
            // Randomly determine how many closest neighbors to consider.
            // This adds diversity to the "closeness" criterion.
            int neighbor_check_limit = std::min((int)neighbors.size(), getRandomNumber(5, 15)); 

            int chosen_neighbor = -1;
            for (int i = 0; i < neighbor_check_limit; ++i) {
                int neighbor = neighbors[i];
                // Ensure the neighbor is a valid customer index and not already selected.
                if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && 
                    selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                    
                    // Introduce a probability to pick this neighbor, favoring closer ones (smaller 'i').
                    // This creates a bias towards proximity but allows for occasional jumps.
                    if (getRandomFractionFast() < 0.95 || i == 0) { // 95% chance to pick, or if it's the very first.
                        chosen_neighbor = neighbor;
                        break; 
                    }
                }
            }

            if (chosen_neighbor != -1) {
                selected_customers_set.insert(chosen_neighbor);
                candidate_found = true;
            }
            num_tries++;
        }

        // Fallback: If no suitable neighbor was found after many tries (e.g., all neighbors are already selected
        // or we're stuck in a small cluster), pick a completely random unselected customer.
        if (!candidate_found) {
            int fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            // Keep trying until an unselected customer is found, or all customers are selected.
            // The `selected_customers_set.size() < sol.instance.numCustomers` condition prevents infinite loops if all are selected.
            while (selected_customers_set.find(fallback_customer) != selected_customers_set.end() && 
                   selected_customers_set.size() < sol.instance.numCustomers) {
                fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            }
            // Only insert if it's genuinely a new customer (not already in set) and we haven't selected all customers yet.
            if (selected_customers_set.find(fallback_customer) == selected_customers_set.end() && 
                selected_customers_set.size() < sol.instance.numCustomers) { 
                 selected_customers_set.insert(fallback_customer);
            } else if (selected_customers_set.size() == sol.instance.numCustomers) {
                // If all customers are already selected, break to avoid infinite loop trying to find a new one.
                break;
            }
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

// Function selecting the order in which to reinsert the removed customers.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Define weights for the scoring function. These weights balance the impact of prize, demand, and randomness.
    const float P_WEIGHT = 1.0;  // Weight for customer prize (higher prize is better)
    const float D_WEIGHT = 0.05; // Weight for customer demand (higher demand is worse, smaller factor as demand scale usually different from prize)
    const float R_WEIGHT = 0.1;  // Weight for the random component to introduce stochasticity

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Find max prize for normalization of the random component, ensuring its impact is relative to typical prize values.
    float max_prize = 0.0; 
    for (int c = 1; c <= instance.numCustomers; ++c) {
        if (instance.prizes[c] > max_prize) {
            max_prize = instance.prizes[c];
        }
    }
    if (max_prize == 0) max_prize = 1.0; // Prevent division by zero if all prizes are zero

    for (int customer_id : customers) {
        float score = 0.0;
        // Base score: Prioritize customers with high prizes and low demand.
        score += instance.prizes[customer_id] * P_WEIGHT;
        score -= instance.demand[customer_id] * D_WEIGHT;
        
        // Add a stochastic component to ensure diversity in ordering over many iterations.
        // The random value is scaled by R_WEIGHT and max_prize to ensure its effect is meaningful
        // but typically doesn't completely overshadow the prize/demand components.
        score += getRandomFractionFast() * R_WEIGHT * max_prize; 

        scored_customers.push_back({score, customer_id});
    }

    // Sort the customers in descending order based on their calculated score.
    // Customers with higher scores will be reinserted first.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original 'customers' vector with the newly sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}