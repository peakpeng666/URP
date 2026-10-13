#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::shuffle
#include <vector>    // For std::vector
#include <cmath>     // For std::min, std::max

// Headers for the specific problem structures
// #include "Instance.h" // Included via AgentDesigned.h indirectly
// #include "Solution.h" // Included via AgentDesigned.h indirectly
// #include "Tour.h"     // Included via AgentDesigned.h indirectly
// #include "Utils.h"    // Included via AgentDesigned.h directly

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> customerPool; // Customers whose neighbors are candidates for selection

    // Determine the number of customers to remove, with stochasticity
    int numCustomersToRemove = getRandomNumber(8, 25); // Slightly wider range for more diversity

    // 1. Select an initial seed customer
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);
    customerPool.push_back(seedCustomer);

    // 2. Iteratively expand the set of selected customers based on proximity
    while (selectedCustomers.size() < numCustomersToRemove) {
        // Fallback: If the customer pool is exhausted or stuck, pick a new random seed
        // This ensures we always reach the target number of customers to remove.
        if (customerPool.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.count(newSeed) && selectedCustomers.size() < sol.instance.numCustomers) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            if (!selectedCustomers.count(newSeed)) { // Only add if not already selected
                selectedCustomers.insert(newSeed);
                customerPool.push_back(newSeed);
            }
            if (selectedCustomers.size() >= numCustomersToRemove) {
                break;
            }
        }

        // Pick a random "parent" customer from the current pool of selected customers
        int parentIdx = getRandomNumber(0, static_cast<int>(customerPool.size()) - 1);
        int parentCustomer = customerPool[parentIdx];

        // Get the neighbors of the parent customer
        const std::vector<int>& adjList = sol.instance.adj[parentCustomer];

        if (adjList.empty()) {
            // If the parent has no neighbors (should be rare for 500+ customers), skip it.
            // To prevent this parent from being picked repeatedly, one could remove it from customerPool
            // but modifying a vector while iterating or picking randomly is tricky.
            // For simplicity and speed, just allow the loop to pick another parent.
            // The `customerPool.empty()` fallback handles eventual exhaustion.
            continue;
        }

        // Select a random neighbor from the top few closest neighbors to encourage spatial locality
        // while maintaining stochasticity. Consider up to 6 closest neighbors (indices 0-5).
        int neighborSelectionLimit = std::min(static_cast<int>(adjList.size()), 6); 
        int neighborIdx = getRandomNumber(0, neighborSelectionLimit - 1);
        int candidateCustomer = adjList[neighborIdx];

        // Add the candidate customer if not already selected
        if (selectedCustomers.find(candidateCustomer) == selectedCustomers.end()) {
            selectedCustomers.insert(candidateCustomer);
            customerPool.push_back(candidateCustomer); // Add to pool for further expansion
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Create a vector of pairs (score, customer_id)
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customer_id : customers) {
        float currentPrize = instance.prizes[customer_id];
        float currentDemand = instance.demand[customer_id];
        float distToDepot = instance.distanceMatrix[0][customer_id];

        // Calculate a composite score: prioritize high prize, then low demand, then low distance to depot.
        // Add a random perturbation to ensure diversity over millions of iterations.
        // The coefficients are chosen to give prizes highest weight, then demand, then distance,
        // while ensuring the random component can slightly alter relative order among similar-scoring customers.
        float score = currentPrize * 1000.0f - currentDemand * 1.0f - distToDepot * 0.1f;
        score += getRandomFraction(-5.0f, 5.0f); // Random jitter

        // Store as (-score, customer_id) because std::sort sorts in ascending order,
        // and we want customers with higher scores to come first.
        scoredCustomers.emplace_back(-score, customer_id);
    }

    // Sort the customers based on their calculated scores
    std::sort(scoredCustomers.begin(), scoredCustomers.end());

    // Reconstruct the original customers vector in the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}