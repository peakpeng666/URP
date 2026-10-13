#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle and std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"

// A thread-local random engine for std::shuffle and other random operations
// not directly covered by `Utils.h` functions that might use an internal engine.
static thread_local std::mt19937 thread_local_gen(std::random_device{}());

// Customer selection heuristic for the LNS framework.
// This function selects a subset of customers to be removed from the current solution.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // For large instances (500+ customers), removing 15-35 customers is a reasonable range.
    // This allows for significant perturbation while keeping the reinsertion problem manageable.
    int numCustomersToRemove = getRandomNumber(15, 35); 

    // Probabilities for different customer selection strategies.
    // These probabilities are tuned to emphasize the "locality" requirement:
    // "each selected customer should be close to at least one or a few other selected customers."
    const double P_PICK_FROM_SELECTED_NEIGHBORS = 0.7; // High chance to pick a geographically close neighbor
    const double P_PICK_FROM_SAME_TOUR_AS_SELECTED = 0.2; // Medium chance to pick from the same tour
    // The remaining probability (0.1) is for a completely random customer, acting as a fallback
    // and ensuring broader exploration.
    
    // Start by selecting one random customer to seed the removal process.
    // This ensures a new starting point in each LNS iteration, contributing to overall stochasticity.
    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initial_customer);

    // Continue selecting customers until the target number of customers to remove is reached.
    while (selectedCustomers.size() < numCustomersToRemove) {
        int customerToAdd = -1;
        double r = getRandomFractionFast(); // Fast random number generation for strategy selection

        // Strategy 1: Attempt to pick a customer from the neighborhood of an already selected customer.
        // This strategy promotes the selection of spatially clustered customers.
        if (r < P_PICK_FROM_SELECTED_NEIGHBORS) {
            std::vector<int> currentSelected(selectedCustomers.begin(), selectedCustomers.end());
            // Shuffle the already selected customers to pick a random one as a starting point for neighbor search.
            std::shuffle(currentSelected.begin(), currentSelected.end(), thread_local_gen); 
            
            for (int current_selected_cust : currentSelected) {
                const auto& neighbors = sol.instance.adj[current_selected_cust];
                // Consider a limited number of the closest neighbors (e.g., 5-15) for efficiency and relevance.
                // The exact number of neighbors to check is also randomized for added diversity.
                int numNeighborsToConsider = std::min((int)neighbors.size(), getRandomNumber(5, 15)); 
                
                std::vector<int> shuffled_neighbors;
                for(int i = 0; i < numNeighborsToConsider; ++i) {
                    shuffled_neighbors.push_back(neighbors[i]);
                }
                // Shuffle the limited set of neighbors to avoid deterministic order of checking.
                std::shuffle(shuffled_neighbors.begin(), shuffled_neighbors.end(), thread_local_gen);

                for (int neighbor : shuffled_neighbors) {
                    // Ensure the candidate neighbor is a valid customer ID (not the depot, ID 0)
                    // and has not been selected yet.
                    if (neighbor > 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                        customerToAdd = neighbor;
                        break; // Found a valid customer, exit neighbor loop
                    }
                }
                if (customerToAdd != -1) break; // Found a customer, exit loop over selected customers
            }
        } 
        
        // Strategy 2: If Strategy 1 failed to find a customer or was not chosen,
        // attempt to pick a customer from the same tour as an already selected customer.
        // This strategy aims to break up existing routes, encouraging exploration of alternative route structures.
        if (customerToAdd == -1 && r < P_PICK_FROM_SELECTED_NEIGHBORS + P_PICK_FROM_SAME_TOUR_AS_SELECTED) {
            std::vector<int> currentSelected(selectedCustomers.begin(), selectedCustomers.end());
            std::shuffle(currentSelected.begin(), currentSelected.end(), thread_local_gen);

            for (int current_selected_cust : currentSelected) {
                int tour_idx = sol.customerToTourMap[current_selected_cust];
                // Validate the tour index to prevent out-of-bounds access.
                if (tour_idx >= 0 && tour_idx < sol.tours.size()) { 
                    const auto& tour_customers = sol.tours[tour_idx].customers;
                    // Create a shuffled copy of the tour customers to pick one randomly.
                    std::vector<int> shuffled_tour_customers = tour_customers;
                    std::shuffle(shuffled_tour_customers.begin(), shuffled_tour_customers.end(), thread_local_gen);

                    for (int tour_cust : shuffled_tour_customers) {
                        // Ensure the candidate tour customer is a valid ID and not already selected.
                        if (tour_cust > 0 && selectedCustomers.find(tour_cust) == selectedCustomers.end()) {
                            customerToAdd = tour_cust;
                            break; // Found a valid customer, exit tour customer loop
                        }
                    }
                }
                if (customerToAdd != -1) break; // Found a customer, exit loop over selected customers
            }
        }
        
        // Strategy 3 (Fallback): If no specific strategy successfully identified a new customer,
        // or if its probability was not chosen, pick a completely random unselected customer.
        // This ensures progress in filling the removal set and introduces broad diversity.
        if (customerToAdd == -1) {
            while (true) {
                int random_customer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(random_customer) == selectedCustomers.end()) {
                    customerToAdd = random_customer;
                    break;
                }
            }
        }
        selectedCustomers.insert(customerToAdd); // Add the chosen customer to the set
    }
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Heuristic for ordering the removed customers before greedy reinsertion.
// This function sorts the `customers` vector in-place.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers; // Stores pairs of (score, customer_id)

    // Determine the maximum time window width among the customers to be reinserted.
    // This value is used for normalization, allowing customers with tighter time windows (smaller width)
    // to receive a higher score for priority.
    float max_tw_width = 0.0f;
    for (int customer_id : customers) {
        if (instance.TW_Width[customer_id] > max_tw_width) {
            max_tw_width = instance.TW_Width[customer_id];
        }
    }

    // Weights for calculating the "constrainedness" score of each customer.
    // These weights are chosen to prioritize customers that are typically more challenging to place
    // due to their time windows, demand, or service time.
    const float WEIGHT_TW_TIGHTNESS = 0.6f; // High weight for time window tightness
    const float WEIGHT_DEMAND = 0.3f;       // Medium weight for customer demand
    const float WEIGHT_SERVICE_TIME = 0.1f; // Lower weight for service time
    const float WEIGHT_RANDOMNESS = 0.05f;  // Small weight for stochasticity to prevent purely deterministic sorting

    for (int customer_id : customers) {
        float score = 0.0f;

        // Contribution of time window tightness: smaller width leads to a higher score.
        score += WEIGHT_TW_TIGHTNESS * (max_tw_width - instance.TW_Width[customer_id]);

        // Contribution of demand: higher demand leads to a higher score.
        score += WEIGHT_DEMAND * instance.demand[customer_id];

        // Contribution of service time: longer service time leads to a higher score.
        score += WEIGHT_SERVICE_TIME * instance.serviceTime[customer_id];
        
        // Add a small random component to the score.
        // This introduces stochasticity into the sorting order, ensuring that the same set of customers
        // might be ordered differently across LNS iterations. This promotes diversity in the greedy reinsertion process.
        score += WEIGHT_RANDOMNESS * getRandomFractionFast();

        scored_customers.push_back({score, customer_id});
    }

    // Sort the customers based on their calculated score in descending order.
    // Customers with higher scores (indicating they are more constrained or "difficult" to place)
    // will be placed earlier in the reinsertion queue. This can help ensure these critical
    // customers are reinserted successfully.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; // Sort by score in descending order
    });

    // Populate the original `customers` vector with the sorted customer IDs.
    for (size_t i = 0; i < scored_customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}