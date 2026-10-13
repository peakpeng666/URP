#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::shuffle
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    // Determine the number of customers to remove stochastically
    // The range 5-20 is a common small number for LNS removals.
    int numCustomersToRemove = getRandomNumber(5, 20); 

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    // 1. Pick an initial random customer to start the removal cluster
    // Customer IDs are 1 to numCustomers.
    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_customer);

    // 2. Iteratively add customers that are close to already selected ones
    // This promotes the "each selected customer should be close to at least one or a few other selected customers" property.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        std::vector<int> candidates;
        
        // Collect potential candidates from the neighborhood of already selected customers.
        // Iterate through each customer already in the selected set.
        for (int sel_cust : selectedCustomersSet) {
            // Consider a small, fixed number of closest neighbors to keep the operation fast.
            // The `adj` list is pre-sorted by distance.
            const auto& neighbors = sol.instance.adj[sel_cust];
            int num_neighbors_to_check = std::min((int)neighbors.size(), 5); // Check up to 5 closest neighbors

            for (int i = 0; i < num_neighbors_to_check; ++i) {
                int potential_neighbor = neighbors[i];
                // Ensure it's a valid customer index (not depot and within customer range)
                // and that it's not already in the selected set.
                if (potential_neighbor > 0 && potential_neighbor <= sol.instance.numCustomers &&
                    selectedCustomersSet.find(potential_neighbor) == selectedCustomersSet.end()) {
                    candidates.push_back(potential_neighbor);
                }
            }
        }

        if (!candidates.empty()) {
            // If candidates are found, pick one randomly to add.
            // This introduces stochasticity and explores different local clusters.
            int chosen_candidate_idx = getRandomNumber(0, candidates.size() - 1);
            selectedCustomersSet.insert(candidates[chosen_candidate_idx]);
        } else {
            // Fallback: If no suitable unselected neighbors are found for any currently selected customer
            // (e.g., all neighbors are already selected, or a small isolated cluster was formed),
            // pick a completely random unselected customer from the entire problem set.
            // This ensures progress and prevents getting stuck if the initial cluster cannot expand further.
            int random_new_customer = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.find(random_new_customer) != selectedCustomersSet.end()) {
                random_new_customer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(random_new_customer);
        }
    }

    // Convert the unordered_set to a vector for return.
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Define different strategies for sorting removed customers.
    // Sorting by "difficulty" metrics often helps greedy reinsertion.
    enum SortStrategy {
        TW_TIGHTNESS,   // Customers with tighter time windows first
        DEMAND,         // Customers with higher demand first
        DIST_DEPOT,     // Customers farthest from the depot first
        SERVICE_TIME,   // Customers with longer service times first
        RANDOM_SHUFFLE  // Purely random order
    };

    SortStrategy chosen_strategy;
    float r = getRandomFractionFast(); // Use a random float to select a strategy stochastically.

    // Assign probabilities to each strategy.
    // A mix of deterministic "difficulty" criteria and pure random helps in exploration.
    if (r < 0.15) { // 15% chance for pure random shuffle
        chosen_strategy = RANDOM_SHUFFLE;
    } else if (r < 0.35) { // 20% chance for TW_TIGHTNESS
        chosen_strategy = TW_TIGHTNESS;
    } else if (r < 0.55) { // 20% chance for DEMAND
        chosen_strategy = DEMAND;
    } else if (r < 0.75) { // 20% chance for DIST_DEPOT
        chosen_strategy = DIST_DEPOT;
    } else { // 25% chance for SERVICE_TIME (remaining probability)
        chosen_strategy = SERVICE_TIME;
    }

    // Handle pure random shuffle separately as it doesn't require calculating scores.
    if (chosen_strategy == RANDOM_SHUFFLE) {
        // Use a thread_local random number generator for performance in multi-threaded contexts if any.
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    } else {
        // For other strategies, calculate a score for each customer.
        // The goal is to sort "harder" customers first.
        // `std::sort` sorts in ascending order, so scores are designed accordingly.
        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size()); // Pre-allocate memory

        for (int cust_id : customers) {
            float score;
            switch (chosen_strategy) {
                case TW_TIGHTNESS:
                    // Smaller TW_Width indicates a tighter window, so it should come first (smaller score).
                    score = instance.TW_Width[cust_id];
                    break;
                case DEMAND:
                    // Larger demand makes it harder, so it should come first (negate for smaller score).
                    score = -instance.demand[cust_id];
                    break;
                case DIST_DEPOT:
                    // Greater distance from depot makes it harder, so it should come first (negate for smaller score).
                    score = -instance.distanceMatrix[0][cust_id];
                    break;
                case SERVICE_TIME:
                    // Longer service time makes it harder, so it should come first (negate for smaller score).
                    score = -instance.serviceTime[cust_id];
                    break;
                default: // Should not happen for non-RANDOM_SHUFFLE strategies
                    score = 0.0;
                    break;
            }
            // Add a small random perturbation to the score.
            // This breaks ties stochastically and introduces more diversity over many iterations.
            score += getRandomFractionFast() * 1e-6; // Very small perturbation
            customer_scores.push_back({score, cust_id});
        }

        // Sort the customers based on their calculated scores.
        std::sort(customer_scores.begin(), customer_scores.end());

        // Update the original `customers` vector with the new sorted order.
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }
    }
}