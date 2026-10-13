#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidates_queue; // Using a vector as a queue for BFS-like expansion

    // Determine the number of customers to remove stochastically
    // This range can be tuned based on problem size and desired perturbation
    int numCustomersToRemove = getRandomNumber(10, 30); 

    // Step 1: Pick an initial seed customer randomly
    // Customers are indexed from 1 to numCustomers
    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_seed);
    candidates_queue.push_back(initial_seed);

    int queue_head_idx = 0; // Index to the current customer being processed from candidates_queue

    // Step 2: Expand the selection by adding neighbors of already selected customers
    while (selectedCustomersSet.size() < numCustomersToRemove && queue_head_idx < candidates_queue.size()) {
        int current_customer = candidates_queue[queue_head_idx];
        queue_head_idx++; // Move to the next customer in the queue

        // Determine stochastically how many of the closest neighbors to check
        int num_neighbors_to_check = getRandomNumber(5, 15); 
        // Probability to add a neighbor if it's not already selected
        float prob_add_neighbor = getRandomFraction(0.6f, 0.9f); 

        int neighbors_processed = 0;
        // Iterate through the nearest neighbors (adj is sorted by distance)
        for (int neighbor_id : sol.instance.adj[current_customer]) {
            if (neighbors_processed >= num_neighbors_to_check) {
                break; // Stop after checking a stochastic number of closest neighbors
            }

            // Ensure the neighbor is a customer node and not already selected
            if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers && 
                selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                
                if (getRandomFraction() < prob_add_neighbor) {
                    selectedCustomersSet.insert(neighbor_id);
                    candidates_queue.push_back(neighbor_id); // Add to queue for future expansion

                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        break; // Target number of customers reached
                    }
                }
            }
            neighbors_processed++;
        }
        
        if (selectedCustomersSet.size() == numCustomersToRemove) {
            break; 
        }

        // If all current candidates have been processed (queue_head_idx reached end of candidates_queue)
        // and we still need more customers, pick another random unselected seed.
        // This allows for selecting multiple disconnected "clusters" of customers.
        if (queue_head_idx == candidates_queue.size() && selectedCustomersSet.size() < numCustomersToRemove) {
            int new_seed = -1;
            const int max_seed_attempts = 100; // Limit attempts to find an unselected seed
            for (int attempt = 0; attempt < max_seed_attempts; ++attempt) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potential_seed) == selectedCustomersSet.end()) {
                    new_seed = potential_seed;
                    break;
                }
            }
            if (new_seed != -1) {
                selectedCustomersSet.insert(new_seed);
                candidates_queue.push_back(new_seed);
                // No need to reset queue_head_idx; the loop condition will naturally pick up new candidates
            } else {
                // Could not find enough unique seeds. This might happen if nearly all customers are selected,
                // or if the instance is very small and dense. Break to prevent infinite loop.
                break; 
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    // Create a set for fast lookup of customers to be reinserted
    std::unordered_set<int> removedCustomersSet(customers.begin(), customers.end());

    struct CustomerScore {
        float score;
        int customer_id;
    };

    std::vector<CustomerScore> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    // --- Feature Extraction and Normalization Setup ---
    // Find min/max values for features among the *currently selected* customers to normalize them
    float max_prize = 0.0f;
    float min_depot_dist = std::numeric_limits<float>::max();
    float max_depot_dist = 0.0f;
    int max_internal_connectivity = 0;

    for (int c : customers) {
        if (instance.prizes[c] > max_prize) {
            max_prize = instance.prizes[c];
        }
        float current_depot_dist = instance.distanceMatrix[0][c];
        if (current_depot_dist < min_depot_dist) {
            min_depot_dist = current_depot_dist;
        }
        if (current_depot_dist > max_depot_dist) {
            max_depot_dist = current_depot_dist;
        }

        int current_internal_conn_count = 0;
        int num_neighbors_to_check = getRandomNumber(5, 15); // Stochastic choice for this pre-pass
        int neighbors_checked = 0;
        for (int neighbor_id : instance.adj[c]) {
            if (neighbors_checked >= num_neighbors_to_check) break;
            // Ensure neighbor_id is a valid customer ID and is also in the removed set
            if (neighbor_id >= 1 && neighbor_id <= instance.numCustomers && removedCustomersSet.count(neighbor_id)) {
                current_internal_conn_count++;
            }
            neighbors_checked++;
        }
        if (current_internal_conn_count > max_internal_connectivity) {
            max_internal_connectivity = current_internal_conn_count;
        }
    }

    // Handle potential division by zero for normalization if all feature values are identical or zero
    if (max_prize == 0.0f) max_prize = 1.0f; 
    if (max_depot_dist == min_depot_dist) {
        // If all depot distances are the same, make the range 1.0 to avoid division by zero
        // This effectively makes this feature contribute uniformly (or 0) after normalization
        if (max_depot_dist == 0.0f) max_depot_dist = 1.0f; // If all are 0, set to 1
        else max_depot_dist += 1.0f; // Otherwise, add a small offset
    }
    if (max_internal_connectivity == 0) max_internal_connectivity = 1;

    // --- Score Calculation for Each Customer ---
    for (int c : customers) {
        // Feature 1: Normalized Prize
        float normalized_prize = instance.prizes[c] / max_prize;
        
        // Feature 2: Normalized Inverse Depot Distance (closer to depot is better)
        float normalized_inv_depot_dist;
        if (instance.distanceMatrix[0][c] == 0.0f) { 
             normalized_inv_depot_dist = 1.0f; // Customer is at depot, max proximity
        } else {
            // Invert distance: (Max_Dist - Current_Dist) / (Max_Dist - Min_Dist)
            normalized_inv_depot_dist = (max_depot_dist - instance.distanceMatrix[0][c]) / (max_depot_dist - min_depot_dist);
        }

        // Feature 3: Normalized Internal Connectivity (how many neighbors are also removed)
        int current_internal_conn_count = 0;
        int num_neighbors_to_check_local = getRandomNumber(5, 15); // Stochastic choice per customer
        int neighbors_checked_local = 0;
        for (int neighbor_id : instance.adj[c]) {
            if (neighbors_checked_local >= num_neighbors_to_check_local) break;
            if (neighbor_id >= 1 && neighbor_id <= instance.numCustomers && removedCustomersSet.count(neighbor_id)) {
                current_internal_conn_count++;
            }
            neighbors_checked_local++;
        }
        float normalized_internal_connectivity = static_cast<float>(current_internal_conn_count) / max_internal_connectivity;

        // Stochastic weights for the features
        float w_prize = getRandomFraction();
        float w_depot_dist = getRandomFraction();
        float w_internal_conn = getRandomFraction();
        float sum_weights = w_prize + w_depot_dist + w_internal_conn;
        
        // Normalize weights to sum to 1 to maintain score scale
        if (sum_weights == 0.0f) { 
            w_prize = 1.0f/3.0f; w_depot_dist = 1.0f/3.0f; w_internal_conn = 1.0f/3.0f;
        } else {
            w_prize /= sum_weights;
            w_depot_dist /= sum_weights;
            w_internal_conn /= sum_weights;
        }
        
        float score = w_prize * normalized_prize + 
                      w_depot_dist * normalized_inv_depot_dist + 
                      w_internal_conn * normalized_internal_connectivity;
        
        scoredCustomers.push_back({score, c});
    }

    // Sort customers in descending order based on their calculated score
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const CustomerScore& a, const CustomerScore& b) {
        return a.score > b.score;
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].customer_id;
    }
}