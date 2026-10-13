#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFraction, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentSelectedCustomersList; // Customers already selected, from which we can expand

    int numCustomersToRemove = getRandomNumber(15, 25); // Target number of customers to remove

    // Step 1: Select an initial random customer as the seed for expansion
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    currentSelectedCustomersList.push_back(initialCustomer);

    int consecutiveFailuresToExpand = 0;
    const int maxConsecutiveFailures = 20; // If unable to expand existing group for this many tries, pick a new random seed
    const int maxAdjNeighborsToConsider = 10; // Only consider the top N closest neighbors from adj list for expansion

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // Fallback mechanism: If we consistently fail to expand the current cluster(s)
        if (consecutiveFailuresToExpand >= maxConsecutiveFailures || currentSelectedCustomersList.empty()) {
            int newSeed = -1;
            // Try to find a new unselected customer to start a new cluster
            for (int i = 0; i < sol.instance.numCustomers * 2; ++i) { // Loop limit for safety
                int potentialNewSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potentialNewSeed) == selectedCustomersSet.end()) {
                    newSeed = potentialNewSeed;
                    break;
                }
            }

            if (newSeed != -1) {
                selectedCustomersSet.insert(newSeed);
                currentSelectedCustomersList.push_back(newSeed);
                consecutiveFailuresToExpand = 0; // Reset failure count for the new cluster
                continue; // Continue to next iteration, attempting to expand from the new seed
            } else {
                // Should theoretically not be reached unless all customers are selected, but for robustness
                break;
            }
        }

        // Pick a random customer from the currently selected ones to serve as an anchor for expansion
        int anchorCustomerIdx = getRandomNumber(0, static_cast<int>(currentSelectedCustomersList.size()) - 1);
        int anchorCustomer = currentSelectedCustomersList[anchorCustomerIdx];

        bool foundNewNeighbor = false;
        int numNeighborsInAdj = sol.instance.adj[anchorCustomer].size();
        int neighborsToProbe = std::min(numNeighborsInAdj, maxAdjNeighborsToConsider);

        // Try to find a new neighbor from the anchor customer's closest neighbors
        // Iterate a few times to increase the chance of finding a unique unselected neighbor
        for (int attempt = 0; attempt < 5; ++attempt) {
            if (neighborsToProbe == 0) break; // No neighbors to probe

            // Randomly select a neighbor from the top 'neighborsToProbe' closest ones
            int neighborIdxInAdj = getRandomNumber(0, neighborsToProbe - 1);
            int potentialNeighbor = sol.instance.adj[anchorCustomer][neighborIdxInAdj];

            if (selectedCustomersSet.find(potentialNeighbor) == selectedCustomersSet.end()) {
                // Found a new, unselected neighbor
                selectedCustomersSet.insert(potentialNeighbor);
                currentSelectedCustomersList.push_back(potentialNeighbor);
                foundNewNeighbor = true;
                consecutiveFailuresToExpand = 0; // Reset failure count as we successfully expanded
                break; // Move to the next customer selection iteration
            }
        }

        if (!foundNewNeighbor) {
            consecutiveFailuresToExpand++; // Increment failure count if no new neighbor was found from this anchor
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

    // Randomly choose one of two main sorting strategies for diversity
    // Strategy 1: Prioritize high demand and customers far from the depot (higher score for these)
    // Strategy 2: Prioritize low demand and customers close to the depot (lower score for these)
    bool prioritizeHighDemandFar = getRandomFractionFast() < 0.5;

    // Random weights for demand and distance components, with a stochastic noise factor
    float demand_weight = getRandomFraction(0.8, 1.2);
    float dist_depot_weight = getRandomFraction(0.8, 1.2);
    float stochastic_noise_factor = getRandomFraction(0.05, 0.15);

    // Adjust weights based on the chosen strategy
    if (!prioritizeHighDemandFar) {
        demand_weight *= -1.0;
        dist_depot_weight *= -1.0;
    }

    // Calculate a reinsertion priority score for each customer
    for (int customer_id : customers) {
        float score = 0.0;
        score += demand_weight * instance.demand[customer_id];
        score += dist_depot_weight * instance.distanceMatrix[0][customer_id]; // Index 0 is the depot
        score += stochastic_noise_factor * getRandomFractionFast(); // Add random noise for slight variations

        customerScores.push_back({score, customer_id});
    }

    // Sort customers based on their calculated scores in ascending order.
    // If 'prioritizeHighDemandFar' is true, higher original values (demand/distance) result in higher scores,
    // so ascending sort places "lower" scores (less critical) first.
    // If 'prioritizeHighDemandFar' is false, higher original values result in lower (more negative) scores,
    // so ascending sort places "lower" scores (more critical for this strategy) first.
    // This provides two distinct but consistent sorting behaviors.
    std::sort(customerScores.begin(), customerScores.end());

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}