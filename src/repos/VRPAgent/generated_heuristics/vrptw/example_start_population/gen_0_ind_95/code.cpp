#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // Required for std::sort and std::shuffle
#include "Utils.h"

// Customer selection
// Selects a subset of customers to remove based on proximity
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    // Determine the number of customers to remove. A small number is typical for LNS,
    // and this range provides stochasticity.
    int numCustomersToSelect = getRandomNumber(15, 35); 

    // Step 1: Pick a random initial customer (seed) to start the removal cluster.
    // Customers are 1-indexed (1 to numCustomers).
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);

    // Step 2: Iteratively add customers close to existing selected customers.
    // This ensures selected customers are "close to at least one or a few other selected customers".
    while (selectedCustomersSet.size() < numCustomersToSelect) {
        bool added_new_customer = false;

        // Convert the set of selected customers to a vector to allow random access for choosing a source.
        std::vector<int> currentSelectedCustomersVec(selectedCustomersSet.begin(), selectedCustomersSet.end());

        // Try to find a neighbor from a randomly chosen source customer within the already selected set.
        // We make several attempts to find a suitable neighbor to ensure robust growth.
        for (int attempt = 0; attempt < 5 && !added_new_customer; ++attempt) {
            // Randomly pick a source customer from the already selected ones.
            int source_customer_idx = getRandomNumber(0, currentSelectedCustomersVec.size() - 1);
            int source_customer = currentSelectedCustomersVec[source_customer_idx];

            // Iterate through neighbors of the source customer.
            // `instance.adj` provides neighbors sorted by distance, which is efficient.
            for (int neighbor_node_id : sol.instance.adj[source_customer]) {
                // Ensure the neighbor is a customer (node ID > 0 and within customer range)
                // and has not already been selected.
                if (neighbor_node_id > 0 && neighbor_node_id <= sol.instance.numCustomers &&
                    selectedCustomersSet.find(neighbor_node_id) == selectedCustomersSet.end()) {
                    
                    selectedCustomersSet.insert(neighbor_node_id);
                    added_new_customer = true;
                    break; // Successfully added one customer, break from neighbor loop.
                }
            }
        }

        // Fallback: If no suitable unselected neighbor was found after multiple attempts
        // (e.g., all neighbors are already selected or source has no valid customer neighbors),
        // pick a completely random unselected customer to ensure progress towards `numCustomersToSelect`.
        if (!added_new_customer) {
            int random_unselected = -1;
            // Iterate up to a certain number of tries to find an unselected customer.
            // In a large instance, this should quickly find one.
            for (int i = 0; i < sol.instance.numCustomers * 2; ++i) { // Limit iterations to prevent infinite loop
                int candidate = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(candidate) == selectedCustomersSet.end()) {
                    random_unselected = candidate;
                    break;
                }
            }
            
            // Add the found random unselected customer.
            // This condition protects against an edge case where all customers are somehow selected
            // before reaching numCustomersToSelect, though highly unlikely given the problem size.
            if (random_unselected != -1) {
                selectedCustomersSet.insert(random_unselected);
            } else {
                // Should theoretically not be reached if numCustomersToSelect <= sol.instance.numCustomers
                // and there are still unselected customers. Break to prevent potential infinite loop.
                break;
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function selecting the order in which to reinsert the customers
// Incorporates stochasticity by choosing between different sorting criteria.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Use a fast random fraction to stochastically choose a sorting strategy.
    float rand_choice = getRandomFractionFast();

    if (rand_choice < 0.4f) {
        // Strategy 1: Sort by Time Window Width (ascending - tightest time windows first).
        // This prioritizes "difficult" customers that have less flexibility.
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.TW_Width[c1] < instance.TW_Width[c2];
        });
    } else if (rand_choice < 0.7f) {
        // Strategy 2: Sort by Time Window Width (descending - widest time windows first).
        // This prioritizes "easy" customers, potentially building a more stable base before
        // fitting in the more constrained ones.
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.TW_Width[c1] > instance.TW_Width[c2];
        });
    } else if (rand_choice < 0.9f) {
        // Strategy 3: Sort by distance from depot (descending - farthest customers first).
        // Farthest customers might be harder to integrate, so prioritizing them could be beneficial.
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] > instance.distanceMatrix[0][c2];
        });
    } else {
        // Strategy 4: Pure random shuffle.
        // Provides maximum diversity and prevents getting stuck in local optima if other criteria
        // consistently lead to poor reinsertions.
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
    
    // Add minor perturbation to the sorted list for increased diversity over millions of iterations.
    // This slightly "jiggles" the order without completely destroying the chosen sorting principle.
    // The number of swaps is random, up to 20% of the customer count.
    int num_perturbations = getRandomNumber(0, static_cast<int>(customers.size() / 5.0f)); 
    for (int i = 0; i < num_perturbations; ++i) {
        if (customers.size() > 1) { // Ensure there are at least two customers to swap
            int idx1 = getRandomNumber(0, customers.size() - 1);
            int idx2 = getRandomNumber(0, customers.size() - 1);
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}