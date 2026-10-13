#include "AgentDesigned.h" // For Solution, Instance, Tour structs
#include <random>           // For std::mt19937, std::random_device (though Utils.h might handle random number generation)
#include <unordered_set>    // For efficient customer set management
#include <vector>           // For customer lists
#include <algorithm>        // For std::sort, std::min
#include <numeric>          // Not strictly needed for these functions, but often useful
#include "Utils.h"          // For getRandomNumber, getRandomFraction, getRandomFractionFast

// Function to select customers for removal
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // Determine the number of customers to remove.
    // This range (10 to 5% of total customers, capped at 50) is chosen to be small
    // for large instances while still allowing meaningful perturbation.
    int numCustomersToRemove = getRandomNumber(10, std::min(50, static_cast<int>(sol.instance.numCustomers * 0.05)));

    // Handle edge cases: if no customers or trying to remove more than available
    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (numCustomersToRemove == 0) { // Always remove at least one if possible
        numCustomersToRemove = 1;
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // Step 1: Pick a random initial seed customer. Customer IDs are typically 1 to numCustomers.
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);

    // Step 2: Iteratively grow the set by selecting neighbors of already selected customers.
    // This ensures selected customers are spatially related, as required.
    // `current_candidate_set` stores unique potential customers to add next.
    std::unordered_set<int> current_candidate_set;
    std::vector<int> candidates_for_selection_vector; // Used for random sampling from candidates

    // Parameter: How many nearest neighbors to consider from each selected customer to add to candidates.
    // A smaller value tends to keep clusters tighter, larger allows for more spread.
    const int numNeighborsToConsider = 5;

    // Add neighbors of the initial seed to the candidate pool
    // Ensure index is within bounds of adj list (adj[0] is depot, adj[1] for customer 1 etc.)
    if (seedCustomer >= 0 && seedCustomer < sol.instance.adj.size()) {
        for (int neighbor_idx = 0; neighbor_idx < std::min(numNeighborsToConsider, static_cast<int>(sol.instance.adj[seedCustomer].size())); ++neighbor_idx) {
            int neighbor_id = sol.instance.adj[seedCustomer][neighbor_idx];
            // Ensure it's a customer (not depot, id > 0) and not already selected
            if (neighbor_id > 0 && neighbor_id <= sol.instance.numCustomers && selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                current_candidate_set.insert(neighbor_id);
            }
        }
    }

    // Loop until enough customers are selected
    while (selectedCustomers.size() < numCustomersToRemove) {
        // If the candidate pool is empty, it means we've run out of connected customers
        // within the current "cluster". This can happen if numCustomersToRemove is large
        // or initial seed is isolated. In such a case, pick another random customer
        // not yet selected to re-seed the process, ensuring continued diversity and progress.
        if (current_candidate_set.empty()) {
            int newSeed = -1;
            // Attempt to find a new unselected customer for a new seed.
            for (int attempts = 0; attempts < 100; ++attempts) { // Limit attempts to prevent infinite loop
                int potentialSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(potentialSeed) == selectedCustomers.end()) {
                    newSeed = potentialSeed;
                    break;
                }
            }

            if (newSeed != -1) {
                selectedCustomers.insert(newSeed);
                // Add neighbors of this new seed to the candidates
                if (newSeed >= 0 && newSeed < sol.instance.adj.size()) {
                    for (int neighbor_idx = 0; neighbor_idx < std::min(numNeighborsToConsider, static_cast<int>(sol.instance.adj[newSeed].size())); ++neighbor_idx) {
                        int neighbor_id = sol.instance.adj[newSeed][neighbor_idx];
                        if (neighbor_id > 0 && neighbor_id <= sol.instance.numCustomers && selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                            current_candidate_set.insert(neighbor_id);
                        }
                    }
                }
            } else { // Fallback if unable to find a new seed after many attempts (highly unlikely for 500+ customers)
                // Fill remaining with pure random customers to reach target size
                while (selectedCustomers.size() < numCustomersToRemove) {
                    int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                    selectedCustomers.insert(randomCustomer);
                }
                break; // Exit the main loop
            }
        }
        
        // If target size reached after adding new seed, break
        if (selectedCustomers.size() >= numCustomersToRemove) {
             break;
        }

        // Convert current_candidate_set to a vector for random selection.
        // This is done on each iteration as candidate_set changes.
        candidates_for_selection_vector.assign(current_candidate_set.begin(), current_candidate_set.end());

        // Pick a random customer from the candidates_for_selection_vector.
        // A simple uniform random choice maintains good diversity and speed.
        if (!candidates_for_selection_vector.empty()) {
            int randomIndex = getRandomNumber(0, candidates_for_selection_vector.size() - 1);
            int customerToAdd = candidates_for_selection_vector[randomIndex];

            selectedCustomers.insert(customerToAdd);
            current_candidate_set.erase(customerToAdd); // Remove from candidate set as it's now selected

            // Add new neighbors of the freshly selected customer to the candidate pool
            if (customerToAdd >= 0 && customerToAdd < sol.instance.adj.size()) {
                for (int neighbor_idx = 0; neighbor_idx < std::min(numNeighborsToConsider, static_cast<int>(sol.instance.adj[customerToAdd].size())); ++neighbor_idx) {
                    int neighbor_id = sol.instance.adj[customerToAdd][neighbor_idx];
                    if (neighbor_id > 0 && neighbor_id <= sol.instance.numCustomers && selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                        current_candidate_set.insert(neighbor_id);
                    }
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function to sort the removed customers for reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // We want to order customers such that greedy reinsertion can make meaningful changes.
    // This heuristic uses a stochastic choice between sorting by distance from the depot
    // and sorting by customer demand, both with a small random perturbation.
    // This introduces diversity in reinsertion strategies over millions of iterations.

    struct CustomerScore {
        int id;
        float score;
    };

    std::vector<CustomerScore> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    // Calculate a rough scale for random perturbation. This helps ensure the noise
    // is relative to the problem's distances or demands.
    float max_value = 0.0f;
    for (int customer_id = 1; customer_id <= instance.numCustomers; ++customer_id) {
        max_value = std::max(max_value, instance.distanceMatrix[0][customer_id]);
        max_value = std::max(max_value, static_cast<float>(instance.demand[customer_id]));
    }
    // Set perturbation scale to a small fraction of the overall max value.
    const float PERTURBATION_SCALE = max_value * 0.02f; // e.g., 2% of the largest relevant value

    // Stochastically decide the primary sorting criterion (distance vs. demand)
    float random_choice_for_criterion = getRandomFraction(); // Between 0.0 and 1.0

    for (int customer_id : customers) {
        float base_score;
        if (random_choice_for_criterion < 0.5) { // 50% chance: Sort primarily by distance from depot
            base_score = instance.distanceMatrix[0][customer_id];
        } else { // 50% chance: Sort primarily by customer demand
            base_score = static_cast<float>(instance.demand[customer_id]);
        }
        
        // Add a small random perturbation to the score.
        // `getRandomFractionFast()` returns [0.0, 1.0]. `* 2.0f - 1.0f` scales it to [-1.0, 1.0].
        // This ensures identical base scores can still have varied relative order.
        base_score += (getRandomFractionFast() * 2.0f - 1.0f) * PERTURBATION_SCALE;

        scoredCustomers.push_back({customer_id, base_score});
    }

    // Sort in descending order based on the final score.
    // If by distance: customers farthest from the depot are reinserted first.
    // If by demand: high-demand customers are reinserted first.
    // Both strategies can guide greedy reinsertion effectively.
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const CustomerScore& a, const CustomerScore& b) {
        return a.score > b.score;
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].id;
    }
}