#include "AgentDesigned.h"
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <unordered_set>
#include <utility>
#include "Utils.h"

// Customer selection heuristic for Large Neighborhood Search (LNS)
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // Determine the number of customers to remove. A range offers stochasticity.
    // For 500 customers, removing 15-30 is ~3-6%, a reasonable "ruin" size.
    int numCustomersToRemove = getRandomNumber(15, 30); 

    // Step 1: Choose an initial seed customer to start the "ruin"
    int seedCustomer = -1;
    std::vector<int> served_customers_list;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            served_customers_list.push_back(i);
        }
    }

    // With 80% probability, pick a seed from currently served customers to focus on improving existing tours.
    // Otherwise (20% or if no customers are served), pick any customer, allowing for insertion of previously unserved ones.
    if (!served_customers_list.empty() && getRandomFraction() < 0.8) {
        seedCustomer = served_customers_list[getRandomNumber(0, served_customers_list.size() - 1)];
    } else {
        seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    selectedCustomers.insert(seedCustomer);

    // Keep a list of all selected customers to enable choosing a new "focus" customer
    // for expansion if the current one exhausts its unselected neighbors.
    std::vector<int> current_selected_list;
    current_selected_list.push_back(seedCustomer);
    
    int current_focus_customer = seedCustomer;

    // Step 2: Iteratively select more customers based on proximity to already selected ones
    // This builds a "cluster" or "connected component" of removed customers.
    while (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> potential_neighbors;
        // Collect unselected neighbors of the current focus customer
        for (int neighbor : sol.instance.adj[current_focus_customer]) {
            if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                potential_neighbors.push_back(neighbor);
            }
        }

        int nextCustomerToAdd = -1;
        if (!potential_neighbors.empty()) {
            // Select one of the top N closest neighbors probabilistically.
            // The `adj` list provides neighbors sorted by distance, so early elements are closest.
            // Considering a limited number of top neighbors (e.g., 20) balances exploitation (closer)
            // with exploration (slightly further, random pick among top).
            int num_top_neighbors_to_consider = std::min((int)potential_neighbors.size(), 20);
            nextCustomerToAdd = potential_neighbors[getRandomNumber(0, num_top_neighbors_to_consider - 1)];
        } else {
            // Fallback strategy if the current focus customer has no unselected neighbors:
            // 1. Try to find a new "focus" customer from the already selected set that *does* have unselected neighbors.
            // 2. If that fails after several attempts, pick a completely random unselected customer.

            bool found_new_focus_with_neighbors = false;
            // Iterate up to 50 times to find a new focus from `current_selected_list`
            for (int attempts = 0; attempts < 50; ++attempts) { 
                if (current_selected_list.empty()) break; // No selected customers to pick a new focus from

                // Pick a random customer from the already selected ones
                current_focus_customer = current_selected_list[getRandomNumber(0, current_selected_list.size() - 1)];
                potential_neighbors.clear();
                for (int neighbor : sol.instance.adj[current_focus_customer]) {
                    if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                        potential_neighbors.push_back(neighbor);
                    }
                }
                if (!potential_neighbors.empty()) {
                    int num_top_neighbors_to_consider = std::min((int)potential_neighbors.size(), 20);
                    nextCustomerToAdd = potential_neighbors[getRandomNumber(0, num_top_neighbors_to_consider - 1)];
                    found_new_focus_with_neighbors = true;
                    break;
                }
            }

            if (!found_new_focus_with_neighbors) {
                // Last resort: If no new candidates found via neighbors of selected customers,
                // pick a completely random unselected customer. This prevents getting stuck.
                int max_attempts_random = sol.instance.numCustomers * 2; 
                for (int i = 0; i < max_attempts_random; ++i) {
                    int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                    if (selectedCustomers.find(rand_cust) == selectedCustomers.end()) {
                        nextCustomerToAdd = rand_cust;
                        break;
                    }
                }
                if (nextCustomerToAdd == -1) { // No more unselected customers available or too hard to find
                    break; // Cannot fulfill numCustomersToRemove
                }
            }
        }

        if (nextCustomerToAdd != -1) {
            selectedCustomers.insert(nextCustomerToAdd);
            current_selected_list.push_back(nextCustomerToAdd); // Add to list for potential future focus
            current_focus_customer = nextCustomerToAdd; // Make the newly added customer the focus for next iteration
        } else {
            break; // Should not happen if fallback is robust, but for safety
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers; // Stores {score, customer_id} pairs

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id];
        // The greedy reinsertion objective is to maximize collected prize minus distance.
        // Prioritize customers with high prize and low travel cost (e.g., close to depot).
        // Distance from depot (node 0) is a quick proxy for travel cost if starting a new tour,
        // or for cost to reach an existing tour.
        score -= instance.distanceMatrix[0][customer_id];

        // Add stochastic noise to the score. This is crucial for diversity over
        // millions of iterations, preventing the search from getting stuck in local optima
        // by slightly perturbing the order of similarly-scored customers.
        // The noise scale is relative to the average prize per customer, keeping it subtle.
        float noise_scale = 0.05 * (instance.total_prizes / instance.numCustomers); // 5% of average prize
        score += getRandomFraction() * noise_scale; 
        
        scored_customers.push_back({score, customer_id});
    }

    // Sort customers in descending order of their calculated score.
    // Customers with higher prize-to-distance ratio will be attempted first.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the original `customers` vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}