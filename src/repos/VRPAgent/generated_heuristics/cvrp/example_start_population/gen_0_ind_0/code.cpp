#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesPool;

    int numCustomersToRemove = getRandomNumber(
        static_cast<int>(sol.instance.numCustomers * 0.03), 
        static_cast<int>(sol.instance.numCustomers * 0.06)
    );
    if (numCustomersToRemove < 15) numCustomersToRemove = 15; // Ensure a minimum
    if (numCustomersToRemove > 30) numCustomersToRemove = 30; // Ensure a maximum for large instances

    int initialSeed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeed);

    int numNeighborsToAdd = getRandomNumber(2, 5);
    for (int i = 0; i < numNeighborsToAdd && i < sol.instance.adj[initialSeed].size(); ++i) {
        int neighbor = sol.instance.adj[initialSeed][i];
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            candidatesPool.push_back(neighbor);
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int nextCustomerToConsider = -1;

        if (candidatesPool.empty()) {
            // If candidates pool is exhausted, pick another random customer not yet selected
            do {
                nextCustomerToConsider = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.find(nextCustomerToConsider) != selectedCustomersSet.end());
        } else {
            // Pick a random customer from the candidates pool
            int idx = getRandomNumber(0, candidatesPool.size() - 1);
            nextCustomerToConsider = candidatesPool[idx];

            // Remove from candidatesPool using swap-and-pop for O(1)
            candidatesPool[idx] = candidatesPool.back();
            candidatesPool.pop_back();

            // If the chosen customer was already selected, pick another one in the next iteration
            if (selectedCustomersSet.find(nextCustomerToConsider) != selectedCustomersSet.end()) {
                continue;
            }
        }

        selectedCustomersSet.insert(nextCustomerToConsider);

        // Add a few of its nearest neighbors to the candidates pool
        numNeighborsToAdd = getRandomNumber(2, 5);
        for (int i = 0; i < numNeighborsToAdd && i < sol.instance.adj[nextCustomerToConsider].size(); ++i) {
            int neighbor = sol.instance.adj[nextCustomerToConsider][i];
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                candidatesPool.push_back(neighbor);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerMetrics;
    customerMetrics.reserve(customers.size());

    // Calculate a 'difficulty' metric for each customer and add stochastic noise
    for (int customerId : customers) {
        float demandComponent = static_cast<float>(instance.demand[customerId]) / instance.vehicleCapacity;
        float distanceComponent = instance.distanceMatrix[0][customerId]; // Distance from depot

        // A combined metric: higher demand and further distance from depot make it "harder"
        // Add a significant random component to ensure diversity in sorting over iterations
        float metric = demandComponent * 100.0f + distanceComponent * 0.1f;
        metric += getRandomFractionFast() * 50.0f; // Add significant random noise

        customerMetrics.push_back({-metric, customerId}); // Negate metric to sort in descending order of difficulty
    }

    // Sort customers based on their calculated metric
    std::sort(customerMetrics.begin(), customerMetrics.end());

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerMetrics[i].second;
    }
}