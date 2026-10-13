#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::min, std::sort
#include "Utils.h"

// Customer selection
// This heuristic aims to select a small, geographically somewhat clustered, but diverse
// set of customers for removal. It starts with a random customer and then iteratively
// adds its nearest neighbors, occasionally picking a new random seed to ensure diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec; // To preserve insertion order, though not strictly required for removal

    // Determine the number of customers to remove.
    // A small, stochastic range is used to balance neighborhood exploration and computational cost.
    int numCustomersToRemove = getRandomNumber(15, 30);

    // Select an initial random customer (customer IDs are 1-indexed).
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    std::vector<int> candidatePool; // Pool of potential customers to add, based on proximity

    // Add closest neighbors of the initial customer to the candidate pool.
    // The `adj` list is 0-indexed, so `initialCustomer - 1` is used to access it.
    // Neighbors are node IDs, which includes the depot (node 0). We only want customers.
    if (initialCustomer >= 1 && initialCustomer <= sol.instance.numCustomers) {
        const auto& adj_initial = sol.instance.adj[initialCustomer - 1];
        // Consider a limited number of closest neighbors to keep the pool manageable and focused.
        int neighbors_to_consider = std::min((int)adj_initial.size(), 20);
        for (int i = 0; i < neighbors_to_consider; ++i) {
            int neighbor_node_id = adj_initial[i];
            // Only add if it's a customer (not depot) and not already selected.
            if (neighbor_node_id != 0 && selectedCustomersSet.count(neighbor_node_id) == 0) {
                candidatePool.push_back(neighbor_node_id);
            }
        }
    }

    // Continue adding customers until the target number is reached.
    while (selectedCustomersVec.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            // If the current neighborhood is exhausted, pick a new random customer
            // that hasn't been selected yet. This ensures diversity and prevents stagnation.
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            // Loop to find an unselected new seed. Limited attempts to prevent infinite loop
            // in highly improbable scenarios (e.g., almost all customers selected).
            while (selectedCustomersSet.count(newSeed) > 0 && attempts < sol.instance.numCustomers * 2) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            // If no new unselected seed can be found after many attempts, break.
            // This should rarely happen given the small numCustomersToRemove.
            if (selectedCustomersSet.count(newSeed) > 0) {
                break;
            }

            selectedCustomersSet.insert(newSeed);
            selectedCustomersVec.push_back(newSeed);

            // Add neighbors of the new seed to the candidate pool.
            if (newSeed >= 1 && newSeed <= sol.instance.numCustomers) {
                const auto& adj_newSeed = sol.instance.adj[newSeed - 1];
                int neighbors_to_consider = std::min((int)adj_newSeed.size(), 20);
                for (int i = 0; i < neighbors_to_consider; ++i) {
                    int neighbor_node_id = adj_newSeed[i];
                    if (neighbor_node_id != 0 && selectedCustomersSet.count(neighbor_node_id) == 0) {
                        candidatePool.push_back(neighbor_node_id);
                    }
                }
            }
        } else {
            // Pick a random customer from the candidate pool to add.
            int poolIdx = getRandomNumber(0, candidatePool.size() - 1);
            int customerToAdd = candidatePool[poolIdx];

            // Efficiently remove the chosen customer from the candidate pool.
            candidatePool[poolIdx] = candidatePool.back();
            candidatePool.pop_back();

            // If the customer hasn't been selected yet, add it.
            if (selectedCustomersSet.count(customerToAdd) == 0) {
                selectedCustomersSet.insert(customerToAdd);
                selectedCustomersVec.push_back(customerToAdd);

                // Add its neighbors to the candidate pool for future expansion.
                if (customerToAdd >= 1 && customerToAdd <= sol.instance.numCustomers) {
                    const auto& adj_customerToAdd = sol.instance.adj[customerToAdd - 1];
                    int neighbors_to_consider = std::min((int)adj_customerToAdd.size(), 20);
                    for (int i = 0; i < neighbors_to_consider; ++i) {
                        int neighbor_node_id = adj_customerToAdd[i];
                        if (neighbor_node_id != 0 && selectedCustomersSet.count(neighbor_node_id) == 0) {
                            candidatePool.push_back(neighbor_node_id);
                        }
                    }
                }
            }
        }
    }

    return selectedCustomersVec;
}

// Function selecting the order in which to reinsert the removed customers.
// This heuristic prioritizes customers that are "harder" to place, specifically
// those with higher demand and those further from the depot. This often helps
// create a more stable route structure during greedy reinsertion.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Using thread_local ensures each thread has its own random number generator,
    // which is important for concurrent execution and avoiding seeding issues.
    static thread_local std::mt19937 gen(std::random_device{}());

    // Sort the customers using a custom comparison lambda.
    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        // Retrieve demand for customers. Customer IDs (c1, c2) are 1-indexed,
        // and directly map to indices in `instance.demand` (where index 0 is depot).
        int demand1 = instance.demand[c1];
        int demand2 = instance.demand[c2];

        // Retrieve distance from the depot (node 0).
        // `distanceMatrix[0][c]` gives distance from depot to node `c`.
        float distFromDepot1 = instance.distanceMatrix[0][c1];
        float distFromDepot2 = instance.distanceMatrix[0][c2];

        // Introduce a small stochastic component. This helps break ties and ensures
        // diversity in sorting order over millions of iterations, even for customers
        // with identical demand and distance from depot.
        float noise1 = getRandomFractionFast() * 0.001f;
        float noise2 = getRandomFractionFast() * 0.001f;

        // Combine demand and distance into a single score.
        // Demand is scaled significantly (e.g., by 1000.0f) to make it the primary
        // sorting criterion. Customers with higher demand should be processed first.
        // For customers with similar demand, those further from the depot are prioritized.
        // The noise is added last to perturb very close scores.
        float score1 = static_cast<float>(demand1) * 1000.0f + distFromDepot1 + noise1;
        float score2 = static_cast<float>(demand2) * 1000.0f + distFromDepot2 + noise2;

        // Sort in descending order (higher score comes first).
        return score1 > score2;
    });
}