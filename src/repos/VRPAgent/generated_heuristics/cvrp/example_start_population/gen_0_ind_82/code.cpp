#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::swap
#include <vector>
#include <utility>   // For std::pair

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatePool;

    // Determine the number of customers to remove stochastically.
    // The range scales with problem size but has reasonable min/max bounds.
    int numCustomersToRemove = getRandomNumber(std::max(5, sol.instance.numCustomers / 100), std::min(40, sol.instance.numCustomers / 10));

    // Ensure at least one customer is removed if there are customers to begin with.
    if (sol.instance.numCustomers > 0 && numCustomersToRemove == 0) {
        numCustomersToRemove = 1;
    } else if (sol.instance.numCustomers == 0) {
        return {}; // No customers to remove if instance is empty
    }

    // Step 1: Pick an initial random customer to start the "removal cluster".
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);

    // Add initial customer's closest neighbors to the candidate pool.
    // The number of neighbors added is stochastic (between 5 and 15, or fewer if customer has less than 15 neighbors).
    int numNeighborsToAdd = getRandomNumber(5, std::min((int)sol.instance.adj[initialCustomer].size(), 15));
    for (int i = 0; i < numNeighborsToAdd; ++i) {
        int neighbor = sol.instance.adj[initialCustomer][i];
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            candidatePool.push_back(neighbor);
        }
    }

    // Step 2: Iteratively select more customers from the candidate pool until target is met.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            // If the candidate pool is empty, it means all neighbors of currently selected customers
            // have either been selected or added to the pool. To continue, we start a new
            // disconnected "removal cluster" from an unselected customer.
            int newStartCustomer = -1;
            const int maxAttempts = 100; // Limit attempts to find an unselected customer
            for (int attempts = 0; attempts < maxAttempts; ++attempts) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                    newStartCustomer = randomCustomer;
                    break;
                }
            }

            if (newStartCustomer != -1) {
                selectedCustomersSet.insert(newStartCustomer);
                numNeighborsToAdd = getRandomNumber(5, std::min((int)sol.instance.adj[newStartCustomer].size(), 15));
                for (int i = 0; i < numNeighborsToAdd; ++i) {
                    int neighbor = sol.instance.adj[newStartCustomer][i];
                    if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                        candidatePool.push_back(neighbor);
                    }
                }
            } else {
                // No more unselected customers available after max attempts, or instance is fully selected.
                break;
            }
        }

        // Select a customer from the candidate pool stochastically.
        int idx = getRandomNumber(0, (int)candidatePool.size() - 1);
        int currentCustomer = candidatePool[idx];

        // Efficiently remove the selected customer from the candidatePool.
        std::swap(candidatePool[idx], candidatePool.back());
        candidatePool.pop_back();

        if (selectedCustomersSet.find(currentCustomer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(currentCustomer);

            // Add the newly selected customer's closest neighbors to the candidate pool.
            // Duplicates in candidatePool are handled by the `selectedCustomersSet` check when picked.
            numNeighborsToAdd = getRandomNumber(5, std::min((int)sol.instance.adj[currentCustomer].size(), 15));
            for (int i = 0; i < numNeighborsToAdd; ++i) {
                candidatePool.push_back(sol.instance.adj[currentCustomer][i]);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    // Generate stochastic weights for demand and distance components.
    // This introduces diversity in sorting strategies across millions of iterations.
    float weightDemand = getRandomFraction(0.5f, 1.5f);
    float weightDistance = getRandomFraction(0.01f, 0.1f);

    for (int customerId : customers) {
        float score = static_cast<float>(instance.demand[customerId]) * weightDemand +
                      instance.distanceMatrix[0][customerId] * weightDistance;
        
        // Add a very small random perturbation to scores.
        // This helps in breaking ties stochastically for customers with similar calculated scores,
        // ensuring more diverse reinsertion orders over time.
        score += getRandomFractionFast() * 1e-6;

        customerScores.push_back({score, customerId});
    }

    // Sort customers by their calculated score in descending order.
    // Customers with higher scores are considered "harder" to place (e.g., high demand, far from depot),
    // and are reinserted first to allow the greedy reinsertion to prioritize them.
    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original customers vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}