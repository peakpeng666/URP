#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::swap
#include <vector>
#include <utility>   // For std::pair

#include "Utils.h"

// Constants for the heuristics
// select_by_llm_1
const int MIN_CUSTOMERS_TO_REMOVE = 15;
const int MAX_CUSTOMERS_TO_REMOVE = 35;
const int NEIGHBORS_TO_CONSIDER = 10; // Number of closest neighbors to add to the candidate pool from each newly selected customer

// sort_by_llm_1
const float W_PRIZE = 1.0f;
const float W_DEMAND = 0.5f;
const float W_DEPOT_DIST = 0.01f;
const float W_RANDOM_SORT = 0.001f;


// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> customerCandidatePool; // Pool of customers to consider adding next, favoring proximity

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // Step 1: Select an initial seed customer
    // Aims to pick a visited customer with higher probability (e.g., 80%) to focus on improving existing tours.
    // If no visited customers or with lower probability, picks a random customer (which might be unvisited)
    // to explore adding new customers.
    int initial_seed_id = -1;
    if (sol.instance.numCustomers > 0) {
        std::vector<int> visited_customers_list;
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (sol.customerToTourMap[i] != -1) {
                visited_customers_list.push_back(i);
            }
        }

        if (getRandomFractionFast() < 0.8f && !visited_customers_list.empty()) {
            initial_seed_id = visited_customers_list[getRandomNumber(0, visited_customers_list.size() - 1)];
        } else {
            initial_seed_id = getRandomNumber(1, sol.instance.numCustomers);
        }
    }

    if (initial_seed_id != -1) {
        selectedCustomers.insert(initial_seed_id);
        // Add closest neighbors of the initial seed to the candidate pool
        // instance.adj contains neighbors sorted by distance, where index 0 is the depot.
        // Customer IDs are 1-indexed.
        if (initial_seed_id >= 1 && initial_seed_id <= sol.instance.numCustomers) {
            const auto& neighbors = sol.instance.adj[initial_seed_id];
            for (int neighbor_id : neighbors) {
                // Ensure neighbor_id is a valid customer ID and not already selected
                if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers &&
                    selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                    customerCandidatePool.push_back(neighbor_id);
                }
                if (customerCandidatePool.size() >= NEIGHBORS_TO_CONSIDER) break; 
            }
        }
    } else {
        return {}; // No customers available to select
    }

    // Step 2: Iteratively select customers, favoring proximity to already selected ones
    while (selectedCustomers.size() < numCustomersToRemove) {
        int next_customer_id = -1;

        // Try to pick from the candidate pool (neighbors of already selected customers)
        if (!customerCandidatePool.empty()) {
            int rand_idx = getRandomNumber(0, customerCandidatePool.size() - 1);
            next_customer_id = customerCandidatePool[rand_idx];

            // Efficiently remove the selected item from the pool by swapping with last and popping
            std::swap(customerCandidatePool[rand_idx], customerCandidatePool.back());
            customerCandidatePool.pop_back();

            // If the chosen customer from the pool was already selected (e.g., via another neighbor),
            // or is invalid, mark it for re-selection via the random fallback.
            if (selectedCustomers.count(next_customer_id) > 0 || next_customer_id < 1 || next_customer_id > sol.instance.numCustomers) {
                next_customer_id = -1;
            }
        }

        // Fallback: If no valid customer was picked from the pool, or pool is empty,
        // pick a completely random unselected customer as a new seed point for expansion.
        if (next_customer_id == -1) {
            std::vector<int> unselected_customers_list;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomers.find(i) == selectedCustomers.end()) {
                    unselected_customers_list.push_back(i);
                }
            }
            if (unselected_customers_list.empty()) { // No more customers to pick
                break;
            }
            next_customer_id = unselected_customers_list[getRandomNumber(0, unselected_customers_list.size() - 1)];
        }

        // Add the chosen customer to the set of selected customers
        selectedCustomers.insert(next_customer_id);

        // Add its closest neighbors to the candidate pool for future iterations
        if (next_customer_id >= 1 && next_customer_id <= sol.instance.numCustomers) {
            const auto& neighbors = sol.instance.adj[next_customer_id];
            int added_count = 0;
            for (int neighbor_id : neighbors) {
                if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers &&
                    selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                    customerCandidatePool.push_back(neighbor_id);
                    added_count++;
                }
                if (added_count >= NEIGHBORS_TO_CONSIDER) break; 
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Use a vector of pairs to store (score, customer_id)
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size()); 

    for (int customer_id : customers) {
        float score = 0.0f;

        // Component 1: Prize value (higher prize, higher score)
        // Prioritizes customers that yield higher total prize for the solution.
        score += instance.prizes[customer_id] * W_PRIZE;

        // Component 2: Demand (higher demand, higher score)
        // Prioritizes larger customers to be reinserted earlier, potentially forcing
        // a new tour or ensuring they fit while capacity is still available.
        score += instance.demand[customer_id] * W_DEMAND;

        // Component 3: Distance from depot (closer to depot, higher score)
        // Customers closer to the depot might be easier to re-integrate into existing tours
        // or form new, short tours efficiently.
        score -= instance.distanceMatrix[0][customer_id] * W_DEPOT_DIST;

        // Component 4: Stochastic element
        // Adds a small random perturbation to break ties and introduce diversity in the ordering
        // across different LNS iterations, preventing getting stuck in local optima.
        score += getRandomFractionFast() * W_RANDOM_SORT;

        scored_customers.push_back({score, customer_id});
    }

    // Sort in descending order of scores.
    // Customers with higher scores will be placed earlier in the reinsertion queue.
    std::sort(scored_customers.begin(), scored_customers.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}