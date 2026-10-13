#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort, std::min
#include <vector>
#include <numeric>   // For std::partial_sum

#include "Utils.h" // For getRandomNumber, getRandomFractionFast

// Step 1: Customer Removal - Select a subset of customers to remove.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> customersToExpandFrom; // Pool of customers from which we will try to find neighbors

    // Determine the number of customers to remove stochastically.
    // This range (e.g., 10-25) provides a balance between local neighborhood destruction
    // and ensuring sufficient changes per iteration for large instances.
    int numCustomersToRemove = getRandomNumber(10, 25); 

    // Ensure at least one customer is selected to avoid empty removal sets.
    if (numCustomersToRemove <= 0) {
        numCustomersToRemove = 1;
    }

    // 1. Select an initial seed customer.
    // A random customer serves as the starting point for a localized destruction.
    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    customersToExpandFrom.push_back(initialSeedCustomer);

    // Parameters for controlling the neighborhood expansion process.
    // N_NEIGHBORS_TO_CONSIDER_PER_NODE limits the number of closest neighbors
    // checked from each expanding customer to maintain high performance.
    const int N_NEIGHBORS_TO_CONSIDER_PER_NODE = 10; 
    // BASE_PROB_ADD_NEIGHBOR sets the initial likelihood of including a neighbor.
    const float BASE_PROB_ADD_NEIGHBOR = 0.8f;      

    // 2. Expand from selected customers until the target number of customers is reached
    // or no more eligible customers are available for expansion.
    while (selectedCustomersSet.size() < numCustomersToRemove && !customersToExpandFrom.empty()) {
        // Randomly pick a customer from the 'customersToExpandFrom' pool.
        // This stochastic choice helps in exploring different destruction patterns over iterations.
        int rand_idx_in_pool = getRandomNumber(0, static_cast<int>(customersToExpandFrom.size()) - 1);
        int current_customer_source = customersToExpandFrom[rand_idx_in_pool];

        // Efficiently remove the selected customer from the pool to avoid redundant expansions
        // and ensure the loop terminates (eventually the pool becomes empty).
        customersToExpandFrom[rand_idx_in_pool] = customersToExpandFrom.back();
        customersToExpandFrom.pop_back();

        // Access the pre-sorted adjacency list for the current source customer.
        // Node IDs are 0 to numNodes-1, where 0 is the depot. Customers are 1 to numCustomers.
        const auto& neighbors_of_source = sol.instance.adj[current_customer_source];
        int neighbors_checked_count = 0;

        for (int neighbor_node_id : neighbors_of_source) {
            // Stop processing neighbors from this source if we have considered enough,
            // or if the overall target number of customers to remove has been met.
            if (neighbors_checked_count >= N_NEIGHBORS_TO_CONSIDER_PER_NODE || 
                selectedCustomersSet.size() == numCustomersToRemove) {
                break;
            }

            // Skip the depot node (ID 0) as it is not a customer to be removed.
            if (neighbor_node_id == 0) {
                continue;
            }

            // If the neighbor is not already in our set of selected customers, consider adding it.
            if (selectedCustomersSet.find(neighbor_node_id) == selectedCustomersSet.end()) {
                // Calculate a probability that decreases as the rank of the neighbor increases (i.e., farther neighbors).
                // This encourages adding closer customers while maintaining some randomness.
                float prob_to_add = BASE_PROB_ADD_NEIGHBOR * 
                                    (1.0f - static_cast<float>(neighbors_checked_count) / N_NEIGHBORS_TO_CONSIDER_PER_NODE * 0.5f); 

                // Use a fast random number generator to make the stochastic decision.
                if (getRandomFractionFast() < prob_to_add) {
                    selectedCustomersSet.insert(neighbor_node_id);
                    // Add the newly selected customer to the pool for further expansion.
                    // This mechanism ensures that selected customers tend to be spatially close to each other.
                    customersToExpandFrom.push_back(neighbor_node_id); 
                }
            }
            neighbors_checked_count++;
        }
    }

    // 3. Fallback: If the neighborhood expansion did not yield enough customers,
    // fill the remaining slots by picking truly random customers.
    // This guarantees that 'numCustomersToRemove' customers are always selected.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomersSet.insert(randomCustomer);
    }

    // Convert the set of selected customers to a vector for return.
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Step 3: Customer Ordering - Order the removed customers using another heuristic.
// The order in which customers are reinserted can significantly impact the final solution quality.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // No sorting needed for zero or one customer.
    if (customers.size() <= 1) {
        return;
    }

    // Use a thread-local random number generator for performance and thread safety.
    static thread_local std::mt19937 gen(std::random_device{}());

    // 1. Stochastic Initialization:
    // Randomly choose one customer to be the first in the reinsertion sequence.
    // This introduces a crucial element of stochasticity to diversify the search.
    int first_customer_idx = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
    std::swap(customers[0], customers[first_customer_idx]);

    // 2. Iterative Nearest Neighbor with Stochastic Choice:
    // For each subsequent position, select the "next" customer from the remaining
    // unplaced customers that is closest to the last placed customer.
    // A probabilistic selection from the top-k closest candidates adds further diversity.
    const int K_CANDIDATES_FOR_PROBABILISTIC_CHOICE = 5; // Consider top K closest neighbors for stochastic choice

    for (size_t i = 1; i < customers.size(); ++i) {
        int last_placed_customer_id = customers[i-1];
        
        // Collect distances for all remaining unsorted customers to the last placed customer.
        std::vector<std::pair<float, int>> remaining_customer_distances; // Stores {distance, customer_id}
        for (size_t j = i; j < customers.size(); ++j) {
            int candidate_customer_id = customers[j];
            float dist = instance.distanceMatrix[last_placed_customer_id][candidate_customer_id];
            remaining_customer_distances.push_back({dist, candidate_customer_id});
        }

        // Sort candidates by distance to efficiently identify the closest ones.
        std::sort(remaining_customer_distances.begin(), remaining_customer_distances.end());

        // Determine how many candidates to consider for the probabilistic selection.
        int num_candidates_to_consider = std::min(static_cast<int>(remaining_customer_distances.size()), K_CANDIDATES_FOR_PROBABILISTIC_CHOICE);
        
        // This case should ideally not be hit if customers.size() > 1 and loop invariants hold.
        // It's a safeguard if for some reason no more candidates are available.
        if (num_candidates_to_consider == 0) {
            break; 
        }

        // Assign probabilities to the top K candidates.
        // A simple inverse rank probability (1st gets 1/1, 2nd gets 1/2, etc.) is used,
        // favoring closer customers but allowing for exploration.
        std::vector<float> probabilities;
        float total_prob_sum = 0.0f;
        for (int k = 0; k < num_candidates_to_consider; ++k) {
            float prob_val = 1.0f / (static_cast<float>(k) + 1.0f); 
            probabilities.push_back(prob_val);
            total_prob_sum += prob_val;
        }

        // Normalize probabilities so they sum to 1.
        for (float& p : probabilities) {
            p /= total_prob_sum;
        }

        // Compute cumulative probabilities to facilitate quick random selection.
        std::vector<float> cumulative_probabilities(num_candidates_to_consider);
        std::partial_sum(probabilities.begin(), probabilities.end(), cumulative_probabilities.begin());

        // Select one candidate probabilistically.
        float r = getRandomFractionFast(); // Random value between 0.0 and 1.0
        int chosen_k = 0;
        for (int k = 0; k < num_candidates_to_consider; ++k) {
            if (r < cumulative_probabilities[k]) {
                chosen_k = k;
                break;
            }
        }
        int chosen_customer_id = remaining_customer_distances[chosen_k].second;

        // Find the chosen customer's current index in the unsorted part of the vector
        // (from index 'i' onwards) and swap it into position 'i'.
        for (size_t j = i; j < customers.size(); ++j) {
            if (customers[j] == chosen_customer_id) {
                std::swap(customers[i], customers[j]);
                break;
            }
        }
    }
}