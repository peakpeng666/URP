#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast etc.

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // Determine the number of customers to remove. A small range is chosen for efficiency
    // and to align with LNS best practices for large instances.
    int numCustomersToRemove = getRandomNumber(10, 20); 

    // Handle edge case where there are no customers to select
    if (sol.instance.numCustomers == 0) {
        return {};
    }

    // 1. Pick a random initial customer to start the "removal cluster".
    // Customer IDs are typically 1 to numCustomers.
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialCustomer);

    // Keep a list of currently selected customers to easily pick a random 'seed' for growing the cluster.
    std::vector<int> currentSelectedList;
    currentSelectedList.push_back(initialCustomer);

    // 2. Iteratively add customers that are close to already selected ones.
    // This promotes the requirement that each selected customer is close to at least one or a few others.
    while (selectedCustomers.size() < numCustomersToRemove) {
        // Stochastic selection: Choose a random customer from the already selected ones.
        // This customer will serve as a 'seed' to find a new customer to remove.
        int seedCustomerIdx = getRandomNumber(0, static_cast<int>(currentSelectedList.size() - 1));
        int seedCustomer = currentSelectedList[seedCustomerIdx];

        bool customerAddedInIteration = false;
        // Limit the search for neighbors to a small number (e.g., top 10 closest) for speed.
        // The adjacency list 'adj' is sorted by distance.
        int maxNeighborsToConsider = std::min(static_cast<int>(sol.instance.adj[seedCustomer].size()), 10); 

        // Introduce stochasticity by starting the neighbor search at a random index
        // within the considered range of closest neighbors.
        int startNeighborIdx = getRandomNumber(0, std::max(0, maxNeighborsToConsider - 1));

        for (int i = 0; i < maxNeighborsToConsider; ++i) {
            // Cycle through the chosen range of neighbors to ensure variety.
            int neighborIndexInAdjList = (startNeighborIdx + i) % maxNeighborsToConsider;
            int neighbor = sol.instance.adj[seedCustomer][neighborIndexInAdjList];

            // Ensure the neighbor is a customer (not the depot, which is node 0)
            // and has not been selected yet.
            if (neighbor != 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                selectedCustomers.insert(neighbor);
                currentSelectedList.push_back(neighbor); // Add to list for future seeding
                customerAddedInIteration = true;
                break; // Found one, move to the next customer selection slot.
            }
        }

        // Fallback mechanism: If the localized search around the seed customer fails
        // to find a new unselected customer (e.g., all neighbors are already selected),
        // pick a truly random unselected customer to ensure the target number is reached.
        if (!customerAddedInIteration) {
            int randomCustomerFallback = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.find(randomCustomerFallback) != selectedCustomers.end()) {
                randomCustomerFallback = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(randomCustomerFallback);
            currentSelectedList.push_back(randomCustomerFallback);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return; // No need to sort an empty or single-element vector
    }

    std::vector<std::pair<int, float>> customerScores;
    customerScores.reserve(customers.size());

    // Calculate a "centrality" score for each removed customer.
    // The score is the average distance to all *other* customers within the removed set.
    // Customers that are more central (lower average distance) will be placed earlier.
    for (int i = 0; i < customers.size(); ++i) {
        int customer_id = customers[i];
        float sum_dist = 0.0f;
        int count = 0;
        for (int j = 0; j < customers.size(); ++j) {
            if (i == j) continue; // Don't compare a customer to itself
            int other_customer_id = customers[j];
            sum_dist += instance.distanceMatrix[customer_id][other_customer_id];
            count++;
        }
        
        float avg_dist = (count > 0) ? (sum_dist / count) : 0.0f;

        // Add stochasticity: perturb the score slightly.
        // This ensures diversity over millions of iterations by breaking ties
        // and slightly altering the order, even for customers with similar average distances.
        // The perturbation range (e.g., -0.01 to 0.01) should be small relative to typical distances.
        float perturbation = getRandomFraction(-0.01f, 0.01f); 
        customerScores.push_back({customer_id, avg_dist + perturbation});
    }

    // Sort customers based on their calculated score in ascending order.
    // Customers with a lower average distance (more central to the removed group)
    // will be reinserted first. This might facilitate more compact or efficient reinsertions.
    std::sort(customerScores.begin(), customerScores.end(),
              [](const std::pair<int, float>& a, const std::pair<int, float>& b) {
                  return a.second < b.second;
              });

    // Update the original 'customers' vector with the new sorted order.
    for (int i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].first;
    }
}