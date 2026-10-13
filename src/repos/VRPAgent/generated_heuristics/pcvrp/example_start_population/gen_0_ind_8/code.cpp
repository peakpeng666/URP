#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20); // Small number as required
    
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentExpansionSources; // Nodes from which to expand the selection

    // 1. Seed selection: Pick a random initial customer
    // Customers are 1-indexed for the problem, 0 is depot.
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    currentExpansionSources.push_back(initialCustomer);

    // 2. Expansion loop: Grow the selection by adding neighbors
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // If current sources are exhausted, pick another random unselected customer to start a new cluster
        if (currentExpansionSources.empty()) {
            int newSeed = -1;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                    newSeed = i;
                    break;
                }
            }
            if (newSeed != -1) {
                selectedCustomersSet.insert(newSeed);
                currentExpansionSources.push_back(newSeed);
                if (selectedCustomersSet.size() == numCustomersToRemove) {
                    break; // Reached target
                }
            } else {
                // All customers are already selected (should only happen if numCustomersToRemove == total customers)
                break;
            }
        }

        // Select a random source node from the current expansion sources
        int sourceIdx = getRandomNumber(0, static_cast<int>(currentExpansionSources.size() - 1));
        int currentSourceNode = currentExpansionSources[sourceIdx];

        bool addedNewCustomerFromSource = false;
        const auto& neighbors = sol.instance.adj[currentSourceNode]; // Neighbors are sorted by distance

        // Iterate through neighbors and stochastically add unselected ones
        for (int neighborId : neighbors) {
            // Ensure neighborId is a customer (1 to numCustomers) and not already selected
            if (neighborId >= 1 && neighborId <= sol.instance.numCustomers &&
                selectedCustomersSet.find(neighborId) == selectedCustomersSet.end()) {
                
                // Stochastic acceptance to introduce diversity and avoid always picking the closest
                if (getRandomFractionFast() < 0.75f) { // 75% chance to add an unselected neighbor
                    selectedCustomersSet.insert(neighborId);
                    currentExpansionSources.push_back(neighborId); // New customer can also be an expansion source
                    addedNewCustomerFromSource = true;
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        goto end_selection_loop; // Exit all loops once target is reached
                    }
                }
            }
        }
        
        // If this source node didn't yield any new customers, and we have other sources,
        // remove it from consideration for next iterations.
        // This helps to prevent getting stuck on nodes with no suitable unselected neighbors.
        if (!addedNewCustomerFromSource && currentExpansionSources.size() > 1) {
            currentExpansionSources.erase(currentExpansionSources.begin() + sourceIdx);
        }
    }

end_selection_loop:; // Label for goto

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Prioritize customers with higher prize values, with a small stochastic perturbation
    // This helps in breaking ties and adding diversity to the search

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        // Calculate a score: base prize + prize * random_perturbation
        // Random perturbation: a value between -0.1 and 0.1 (i.e., +/- 10% of the prize)
        float perturbation = getRandomFraction(-0.1f, 0.1f);
        float score = instance.prizes[customerId] * (1.0f + perturbation);
        customerScores.push_back({score, customerId});
    }

    // Sort the customers in descending order based on their calculated score (highest score first)
    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}