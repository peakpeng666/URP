#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> potentialExpansionNodes;

    // Determine the number of customers to remove.
    // Range selected to be small (10-30) relative to total customers (500+).
    int numCustomersToRemove = getRandomNumber(10, 30);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // 1. Select an initial seed customer randomly.
    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    potentialExpansionNodes.push_back(initialSeedCustomer);

    // 2. Expand the selection by iteratively adding neighbors of already selected customers.
    // This process encourages the selected customers to be spatially close to each other.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (potentialExpansionNodes.empty()) {
            // Fallback: If the current "cluster" of selected customers cannot expand further
            // (e.g., all neighbors are already selected or no more neighbors left to consider
            // from the current pool), pick a new random unselected customer as a new seed.
            // This ensures that the required number of customers are always selected,
            // even if they form disjoint "removal clusters".
            int newSeedFound = -1;
            while (newSeedFound == -1) {
                int tempSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(tempSeed) == selectedCustomersSet.end()) {
                    newSeedFound = tempSeed;
                }
            }
            selectedCustomersSet.insert(newSeedFound);
            potentialExpansionNodes.push_back(newSeedFound);
            if (selectedCustomersSet.size() == numCustomersToRemove) {
                break;
            }
        }

        // Randomly pick a customer from the pool of currently selected customers
        // that can be used as a pivot for expansion.
        int pivotIndex = getRandomNumber(0, potentialExpansionNodes.size() - 1);
        int pivotCustomer = potentialExpansionNodes[pivotIndex];

        // Remove the pivot from the expansion pool after it's processed for this iteration.
        // This mimics a breadth-first-like expansion where each selected node gets a chance
        // to extend the cluster via its neighbors.
        potentialExpansionNodes.erase(potentialExpansionNodes.begin() + pivotIndex);

        bool addedAnyNeighbor = false;
        // Iterate through the neighbors of the pivot customer.
        // The 'adj' list is assumed to be sorted by distance, so closer neighbors are considered first.
        for (int neighbor : sol.instance.adj[pivotCustomer]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                // Stochastic decision: Add neighbor with a certain probability (e.g., 80%).
                // This introduces diversity in the shape and density of the removed cluster over iterations.
                if (getRandomFraction() < 0.8) {
                    selectedCustomersSet.insert(neighbor);
                    potentialExpansionNodes.push_back(neighbor); // Add new neighbor to pool for future expansion
                    addedAnyNeighbor = true;
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        break;
                    }
                }
            }
            // If at least one neighbor was added from this pivot,
            // there's a chance (e.g., 30%) to stop considering more neighbors from this pivot.
            // This prevents the selection from becoming too concentrated around a single pivot,
            // encouraging expansion from other points in the growing cluster.
            if (addedAnyNeighbor && getRandomFraction() < 0.3) {
                break;
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Prepare a vector to store pairs of (score, customer_id)
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    // Calculate an average prize per customer to scale the random noise.
    // This makes the stochastic component meaningful relative to the actual prize values.
    float averagePrizePerCustomer = 0.0f;
    if (instance.numCustomers > 0) {
        averagePrizePerCustomer = instance.total_prizes / instance.numCustomers;
    }

    // Calculate a score for each customer to determine its reinsertion priority.
    // The score combines prize value and proximity to the depot, with added stochasticity.
    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id]; // Depot is node 0

        // Base score: Prioritize customers with higher prizes and lower distances to the depot.
        // The multiplier (0.1f) for distance can be tuned to adjust its relative importance.
        float score = prize - dist_to_depot * 0.1f;

        // Add stochastic noise to the score.
        // This ensures that even customers with similar objective-based scores have their
        // relative reinsertion order perturbed across iterations, promoting search diversity.
        // The noise is scaled by a fraction of the average prize to keep it relevant but not dominant.
        score += getRandomFraction() * (averagePrizePerCustomer * 0.5f);

        customerScores.push_back({score, customer_id});
    }

    // Sort the customers in descending order of their calculated scores.
    // Customers with higher scores (more prize, less distance, plus random nudge)
    // will be considered for reinsertion first.
    std::sort(customerScores.rbegin(), customerScores.rend());

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}