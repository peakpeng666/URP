#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility> // For std::pair
#include "Utils.h" // For getRandomNumber, getRandomFraction etc.

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(5, 20); // Small number of customers to remove
    std::unordered_set<int> selectedCustomers;

    int overall_attempts = 0;
    const int max_overall_attempts = 500; // Safety break for the main loop

    while (selectedCustomers.size() < numCustomersToRemove && overall_attempts < max_overall_attempts) {
        int current_customer_id;
        bool found_start_node = false;

        // Option 1: Try to start from an unvisited customer with a 10% probability
        if (getRandomFraction() < 0.1) {
            int attempts_for_unvisited = 0;
            const int max_attempts_for_unvisited = 10;
            while (attempts_for_unvisited < max_attempts_for_unvisited && !found_start_node) {
                int random_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
                if (sol.customerToTourMap[random_customer_idx] == -1) {
                    current_customer_id = random_customer_idx;
                    found_start_node = true;
                }
                attempts_for_unvisited++;
            }
        }

        // Option 2: If no unvisited customer found after attempts, or didn't choose to try for one, pick any random customer
        if (!found_start_node) {
            current_customer_id = getRandomNumber(1, sol.instance.numCustomers);
        }

        // Add the starting customer if not already selected
        if (selectedCustomers.find(current_customer_id) == selectedCustomers.end()) {
            selectedCustomers.insert(current_customer_id);
        } else {
            overall_attempts++;
            continue; // This starting customer was already selected, try a new one
        }

        // Build a short chain of connected customers from the current_customer_id
        int chain_length = getRandomNumber(1, 3); // Build a chain of 1 to 3 additional customers
        for (int i = 0; i < chain_length && selectedCustomers.size() < numCustomersToRemove; ++i) {
            bool added_neighbor = false;
            const auto& neighbors = sol.instance.adj[current_customer_id];
            const int max_neighbors_to_consider = std::min((int)neighbors.size(), 5); // Consider up to 5 closest neighbors

            // Iterate through closest neighbors to find one to add to the chain
            for (int j = 0; j < max_neighbors_to_consider; ++j) {
                int neighbor_id = neighbors[j];
                if (selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                    // Add neighbor with a probability that decreases with its rank in the adjacency list (closer neighbors more likely)
                    if (getRandomFraction() < (1.0 / (float)(j + 1)) * 0.8) { // Stochastic element
                        selectedCustomers.insert(neighbor_id);
                        current_customer_id = neighbor_id; // Continue chain from this new neighbor
                        added_neighbor = true;
                        break; // Move to the next link in the chain
                    }
                }
            }
            if (!added_neighbor) {
                // Could not extend the current chain, break and potentially start a new chain in the next overall iteration
                break;
            }
        }
        overall_attempts++;
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        // Calculate a score for each customer: Prize minus distance from the depot.
        // This prioritizes high-prize customers and those easily accessible from the depot.
        float score = instance.prizes[customer_id] - instance.distanceMatrix[0][customer_id];

        // Add stochastic noise to the score to ensure diversity across iterations
        // The noise range is relative to the average prize to keep it meaningful
        float avg_prize = instance.total_prizes / instance.numCustomers;
        float noise_range = avg_prize * 0.5f; // E.g., noise can be up to 50% of the average prize
        score += getRandomFraction(-noise_range, noise_range);

        customer_scores.push_back({score, customer_id});
    }

    // Sort customers in descending order based on their calculated score
    // std::sort with rbegin/rend sorts in descending order.
    std::sort(customer_scores.rbegin(), customer_scores.rend());

    // Update the original customers vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}