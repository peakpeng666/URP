#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort and std::shuffle
#include "Utils.h"
#include "Solution.h" // Assuming Solution struct is defined here or via AgentDesigned.h
#include "Instance.h" // Assuming Instance struct is defined here or via AgentDesigned.h


// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 25; // Adjusted range for diversity and problem size
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    // Number of closest neighbors to consider for expansion
    int numNeighborsToScan = 15; // Scan a fixed number of closest neighbors
    
    // Probability of picking a new random seed vs. expanding an existing cluster
    float newSeedProbability = 0.2f; 

    while (selectedCustomers.size() < numCustomersToRemove) {
        int sourceCustomerId;
        bool pickedFromSelected = false;

        if (selectedCustomers.empty() || getRandomFractionFast() < newSeedProbability) {
            // Pick a completely random customer as a new seed
            sourceCustomerId = getRandomNumber(1, sol.instance.numCustomers);
        } else {
            // Pick a random customer from the already selected ones to expand the cluster
            std::vector<int> currentSelectedVec(selectedCustomers.begin(), selectedCustomers.end());
            sourceCustomerId = currentSelectedVec[getRandomNumber(0, currentSelectedVec.size() - 1)];
            pickedFromSelected = true;
        }

        // If the source customer is already selected, or if we picked a new seed but it's already selected
        if (selectedCustomers.count(sourceCustomerId) && !pickedFromSelected) {
            // If it's a new seed, but it was already in the set, skip to next iteration
            continue;
        }
        
        // Add the source customer if it's a new one or not yet added
        if (!selectedCustomers.count(sourceCustomerId)) {
            selectedCustomers.insert(sourceCustomerId);
            if (selectedCustomers.size() == numCustomersToRemove) {
                break;
            }
        }

        // Try to add neighbors of the source customer
        std::vector<int> potentialAdditions;
        const auto& adjList = sol.instance.adj[sourceCustomerId];

        // Iterate through closest neighbors
        for (size_t i = 0; i < std::min((size_t)numNeighborsToScan, adjList.size()); ++i) {
            int neighborId = adjList[i];
            // Ensure neighbor is a customer (not depot, which is node 0) and not already selected
            if (neighborId != 0 && !selectedCustomers.count(neighborId)) {
                potentialAdditions.push_back(neighborId);
            }
        }

        if (!potentialAdditions.empty()) {
            // Randomly select one from the potential additions
            int customerToAdd = potentialAdditions[getRandomNumber(0, potentialAdditions.size() - 1)];
            selectedCustomers.insert(customerToAdd);
        } else {
            // If no unselected neighbors are found in the scan range for this source,
            // the loop will continue and pick another source (either new seed or existing).
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());

    // Use a random probability to choose a sorting strategy
    float randVal = getRandomFractionFast();

    if (randVal < 0.33f) {
        // Strategy 1: Sort by descending distance from the depot (customer ID 0 is depot)
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] > instance.distanceMatrix[0][c2];
        });
    } else if (randVal < 0.66f) {
        // Strategy 2: Sort by descending customer demand
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.demand[c1] > instance.demand[c2];
        });
    } else {
        // Strategy 3: Random shuffle (as a diversification)
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}