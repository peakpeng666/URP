#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 25); // Number of customers to remove (10-25)

    // Ensure we don't try to remove more customers than available
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1; // Always remove at least one if customers exist
    } else if (sol.instance.numCustomers == 0) {
        return {}; // No customers to remove
    }

    // Step 1: Select an initial seed customer
    selectedCustomers.insert(getRandomNumber(1, sol.instance.numCustomers));

    // Step 2: Iteratively expand the selection
    std::vector<int> currentSelectionVector; // Used to pick a random customer from current selection

    while (selectedCustomers.size() < numCustomersToRemove) {
        // Option A: With a probability, jump to a completely random customer
        if (getRandomFraction() < 0.25f) { // 25% chance to jump
            selectedCustomers.insert(getRandomNumber(1, sol.instance.numCustomers));
        }
        // Option B: Otherwise, expand from an already selected customer's neighborhood
        else {
            currentSelectionVector.assign(selectedCustomers.begin(), selectedCustomers.end());
            if (currentSelectionVector.empty()) { // Should not happen if a seed is always inserted
                break;
            }
            int current_node = currentSelectionVector[getRandomNumber(0, currentSelectionVector.size() - 1)];

            const auto& neighbors = sol.instance.adj[current_node];

            if (neighbors.empty()) {
                // If the current_node has no neighbors, try another iteration (might jump to random)
                continue;
            }

            // Determine how many closest neighbors to consider (stochastic)
            int min_neighbors_to_consider = std::min((int)neighbors.size(), 3);
            int max_neighbors_to_consider = std::min((int)neighbors.size(), 10);

            if (min_neighbors_to_consider > max_neighbors_to_consider) { // Handle case where size is less than 3
                min_neighbors_to_consider = std::min((int)neighbors.size(), 1);
                max_neighbors_to_consider = std::min((int)neighbors.size(), 1);
            }
            
            if (min_neighbors_to_consider == 0) { // No valid neighbors
                continue;
            }

            int k_neighbors_to_consider = getRandomNumber(min_neighbors_to_consider, max_neighbors_to_consider);
            
            // Pick a random neighbor from the top-k closest neighbors
            int chosen_neighbor_idx = getRandomNumber(0, k_neighbors_to_consider - 1);
            int next_node = neighbors[chosen_neighbor_idx];

            // Ensure the selected node is a customer (not the depot, node 0)
            if (next_node >= 1 && next_node <= sol.instance.numCustomers) {
                selectedCustomers.insert(next_node);
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Create a vector of pairs to store (score, customer_id)
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    // Calculate a "reinsertion score" for each customer
    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id];

        // Stochastic weight for distance to depot
        float dynamic_weight = getRandomFraction(0.5f, 2.0f); 

        // Score based on prize and weighted distance to depot
        // Higher score means more "desirable" for earlier reinsertion
        float score = prize - dist_to_depot * dynamic_weight;

        // Add a small random noise to scores for stochastic tie-breaking and diversity
        score += getRandomFraction(-0.01f, 0.01f); 

        customerScores.push_back({score, customer_id});
    }

    // Sort customers based on their scores in descending order
    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first; // Sort from highest score to lowest
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }

    // With a small probability, reverse the entire sorted list to introduce high diversity
    if (getRandomFraction() < 0.1f) { // 10% chance to reverse the order
        std::reverse(customers.begin(), customers.end());
    }
}