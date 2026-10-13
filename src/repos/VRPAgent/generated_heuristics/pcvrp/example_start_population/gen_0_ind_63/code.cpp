#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::min
#include <vector>    // For std::vector
#include <limits>    // For std::numeric_limits
#include "Utils.h"

// Customer selection heuristic
// This heuristic aims to select a small number of customers for removal,
// favoring customers that are close to each other, to encourage localized changes.
// It incorporates stochastic behavior for diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove.
    // A slightly wider range (10-25) compared to the example (10-20) for more diversity.
    int numCustomersToRemove = getRandomNumber(10, 25); 

    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatePool;         // Customers that are neighbors of already selected customers
    std::unordered_set<int> inCandidatePool; // Efficient lookup for customers in candidatePool

    // Step 1: Select an initial seed customer.
    // The customer IDs are 1-indexed.
    int firstSeed = getRandomNumber(1, sol.instance.numCustomers); 
    selectedCustomers.insert(firstSeed);

    // Add a limited number of the closest neighbors of the first seed to the candidate pool.
    // This helps in forming a localized cluster.
    int maxNeighborsToConsider = std::min((int)sol.instance.adj[firstSeed].size(), 10);
    for (int k = 0; k < maxNeighborsToConsider; ++k) {
        int neighbor = sol.instance.adj[firstSeed][k];
        // Ensure the neighbor is not already selected or in the candidate pool.
        if (selectedCustomers.find(neighbor) == selectedCustomers.end() && 
            inCandidatePool.find(neighbor) == inCandidatePool.end()) {
            candidatePool.push_back(neighbor);
            inCandidatePool.insert(neighbor);
        }
    }

    // Step 2: Iteratively select additional customers until the target number is reached.
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            // If the candidate pool is exhausted (e.g., all neighbors from selected customers are already selected),
            // pick another random customer as a new seed to start a new "cluster" or disconnected removal.
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            // Ensure the new seed is not already selected.
            while (selectedCustomers.find(newSeed) != selectedCustomers.end()) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(newSeed);

            // Add close neighbors of the new seed to the candidate pool.
            maxNeighborsToConsider = std::min((int)sol.instance.adj[newSeed].size(), 10);
            for (int k = 0; k < maxNeighborsToConsider; ++k) {
                int neighbor = sol.instance.adj[newSeed][k];
                if (selectedCustomers.find(neighbor) == selectedCustomers.end() && 
                    inCandidatePool.find(neighbor) == inCandidatePool.end()) {
                    candidatePool.push_back(neighbor);
                    inCandidatePool.insert(neighbor);
                }
            }
        } else {
            // Select a random customer from the current candidate pool.
            int idx = getRandomNumber(0, candidatePool.size() - 1);
            int chosenCustomer = candidatePool[idx];

            // Remove the chosen customer from candidatePool efficiently.
            candidatePool[idx] = candidatePool.back();
            candidatePool.pop_back();
            inCandidatePool.erase(chosenCustomer);

            // If the customer was already selected (e.g., it was a neighbor of multiple selected customers
            // and later directly chosen as a seed), skip and pick another.
            if (selectedCustomers.find(chosenCustomer) != selectedCustomers.end()) {
                continue; 
            }
            
            selectedCustomers.insert(chosenCustomer);

            // Add a limited number of the chosen customer's closest neighbors to the candidate pool.
            maxNeighborsToConsider = std::min((int)sol.instance.adj[chosenCustomer].size(), 10);
            for (int k = 0; k < maxNeighborsToConsider; ++k) {
                int neighbor = sol.instance.adj[chosenCustomer][k];
                if (selectedCustomers.find(neighbor) == selectedCustomers.end() && 
                    inCandidatePool.find(neighbor) == inCandidatePool.end()) {
                    candidatePool.push_back(neighbor);
                    inCandidatePool.insert(neighbor);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers.
// This heuristic prioritizes customers with high prizes and those that are
// part of a tightly connected "sub-cluster" within the set of removed customers.
// It also includes a small random component for diversity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Use an unordered_set for O(1) average-time lookup of removed customers,
    // which is needed to efficiently check if a neighbor is also removed.
    std::unordered_set<int> removedSet(customers.begin(), customers.end());

    // Vector to store (score, customer_id) pairs for sorting.
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size()); // Pre-allocate memory for efficiency.

    // Parameters for tuning the balance between prize and connectedness.
    // EPSILON: Small value to prevent division by zero for very small distances.
    // CONNECTEDNESS_BONUS_SCALE: Multiplier to make the connectedness bonus significant.
    // RANDOM_PERTURBATION_SCALE: Magnitude of random noise for tie-breaking and diversity.
    const float EPSILON = 0.1f; 
    const float CONNECTEDNESS_BONUS_SCALE = 500.0f; 
    const float RANDOM_PERTURBATION_SCALE = 0.1f; 

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float min_dist_to_other_removed = std::numeric_limits<float>::max();
        bool found_close_removed_neighbor = false;

        // Iterate through a limited number of the closest neighbors (from adj list, already sorted by distance)
        // to find the closest one that is also present in the set of removed customers.
        int maxNeighborsToConsider = std::min((int)instance.adj[customer_id].size(), 5); 
        for (int k = 0; k < maxNeighborsToConsider; ++k) {
            int neighbor_id = instance.adj[customer_id][k];
            // Check if the neighbor is different from the customer itself and is part of the removed set.
            if (neighbor_id != customer_id && removedSet.count(neighbor_id)) {
                float dist = instance.distanceMatrix[customer_id][neighbor_id];
                if (dist < min_dist_to_other_removed) {
                    min_dist_to_other_removed = dist;
                    found_close_removed_neighbor = true;
                }
                // Since the adjacency list is sorted by distance, the first found removed neighbor is the closest.
                break; 
            }
        }

        float connectedness_bonus = 0.0f;
        if (found_close_removed_neighbor) {
            // Apply a bonus inversely proportional to the minimum distance to another removed customer.
            // This favors customers that are very close to other removed customers, encouraging re-formation
            // of compact clusters during greedy reinsertion.
            connectedness_bonus = CONNECTEDNESS_BONUS_SCALE / (min_dist_to_other_removed + EPSILON);
        } else if (removedSet.size() == 1) {
            // If this is the only customer in the 'customers' list, there's no other removed customer to connect with.
            connectedness_bonus = 0.0f;
        }
        // If 'found_close_removed_neighbor' is false and 'removedSet.size() > 1', it means the customer
        // is isolated from other removed customers within the 'maxNeighborsToConsider' range.
        // In this case, connectedness_bonus remains 0.0f.

        // Calculate the total score:
        // High prize contributes positively.
        // High connectedness bonus contributes positively (meaning it's part of a dense group of removed customers).
        // A small random perturbation is added for stochasticity and to break ties.
        float score = prize + connectedness_bonus + getRandomFractionFast() * RANDOM_PERTURBATION_SCALE;
        scoredCustomers.push_back({score, customer_id});
    }

    // Sort customers in descending order based on their calculated scores.
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; 
              });

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}