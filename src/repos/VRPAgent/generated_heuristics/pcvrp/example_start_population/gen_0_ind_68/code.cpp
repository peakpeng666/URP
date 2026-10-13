#include "AgentDesigned.h"
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility> // For std::pair
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> expansion_queue;

    int numCustomersToRemove = getRandomNumber(10, 20);

    // Ensure we don't try to remove more customers than available
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    while (selectedCustomers_set.size() < numCustomersToRemove) {
        // Find a random unselected customer to start a new cluster/expansion
        int start_customer_id = -1;
        
        // Start search from a random customer index to find an unselected one
        int initial_search_idx = getRandomNumber(1, sol.instance.numCustomers);
        for (int i = 0; i < sol.instance.numCustomers; ++i) {
            // Cycle through all customer IDs (1 to numCustomers)
            int current_customer_idx = (initial_search_idx + i - 1) % sol.instance.numCustomers + 1;
            if (selectedCustomers_set.find(current_customer_idx) == selectedCustomers_set.end()) {
                start_customer_id = current_customer_idx;
                break;
            }
        }
        
        if (start_customer_id == -1) { // No unselected customers left
            break; 
        }

        selectedCustomers_set.insert(start_customer_id);
        expansion_queue.push_back(start_customer_id);
        int head = 0;

        // BFS-like expansion from the start_customer_id
        while (head < expansion_queue.size() && selectedCustomers_set.size() < numCustomersToRemove) {
            int current_node_id = expansion_queue[head++];

            // Determine how many of the nearest neighbors to explore
            // Ensure this number is within valid bounds and adds stochasticity
            int num_neighbors_to_explore = std::min((int)sol.instance.adj[current_node_id].size(), getRandomNumber(2, 10));

            for (int i = 0; i < num_neighbors_to_explore; ++i) {
                int neighbor_id = sol.instance.adj[current_node_id][i];

                if (selectedCustomers_set.size() >= numCustomersToRemove) {
                    break; // Target number of customers reached
                }

                // Add neighbor with a certain probability to introduce stochasticity
                if (getRandomFractionFast() < 0.85f) { // 85% chance to consider adding a neighbor
                    if (selectedCustomers_set.find(neighbor_id) == selectedCustomers_set.end()) {
                        selectedCustomers_set.insert(neighbor_id);
                        expansion_queue.push_back(neighbor_id);
                    }
                }
            }
        }
        // Clear expansion queue for the next potential cluster, if target not yet met
        expansion_queue.clear();
    }

    std::vector<int> result(selectedCustomers_set.begin(), selectedCustomers_set.end());
    return result;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers primarily by their prize, with a small random perturbation
    // to introduce stochasticity and diversity. This prioritizes reinsertion
    // of high-prize customers, which is aligned with PCVRP objective.

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // Define a scale for the random noise.
    // This makes the noise relative to the overall prize magnitudes,
    // ensuring it's impactful but doesn't completely override large prize differences.
    float prize_noise_scale = instance.total_prizes * 0.005f; // 0.5% of total prize sum as noise scale

    for (int customer_id : customers) {
        float effective_prize = instance.prizes[customer_id] + getRandomFractionFast() * prize_noise_scale;
        customer_scores.emplace_back(effective_prize, customer_id);
    }

    // Sort in descending order based on the calculated effective_prize
    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}