#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFraction

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    const Instance& instance = sol.instance;

    int numCustomersToRemove = getRandomNumber(10, 25);

    float newSeedProbability = 0.25f; // Probability to start a new cluster

    int firstCustomer = getRandomNumber(1, instance.numCustomers);
    selectedCustomersSet.insert(firstCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (getRandomFraction() < newSeedProbability || selectedCustomersSet.empty()) {
            // Option A: Pick a new random customer as a seed for a new cluster
            // This ensures diversity and prevents being stuck if all neighbors are selected
            int newCustomerCandidate = getRandomNumber(1, instance.numCustomers);
            if (selectedCustomersSet.find(newCustomerCandidate) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(newCustomerCandidate);
            }
        } else {
            // Option B: Expand an existing cluster by picking a neighbor of an already selected customer
            std::vector<int> currentSelectedVec(selectedCustomersSet.begin(), selectedCustomersSet.end());
            int baseCustomerIdx = getRandomNumber(0, currentSelectedVec.size() - 1);
            int baseCustomer = currentSelectedVec[baseCustomerIdx];

            bool neighborAdded = false;
            const std::vector<int>& neighbors = instance.adj[baseCustomer]; 

            for (int neighbor : neighbors) {
                if (neighbor > 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(neighbor);
                    neighborAdded = true;
                    break; 
                }
            }

            if (!neighborAdded) {
                // Fallback: If no unselected neighbor was found for the chosen baseCustomer,
                // pick a totally random customer to ensure progress.
                int newCustomerCandidate = getRandomNumber(1, instance.numCustomers);
                if (selectedCustomersSet.find(newCustomerCandidate) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(newCustomerCandidate);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    // Weights for different factors influencing difficulty/priority
    float weightTW = 3.0f;         
    float weightServiceTime = 1.0f;  
    float weightDemand = 2.0f;       
    float weightDistance = 0.5f;     

    float perturbationRange = 0.1f; 

    for (int customerId : customers) {
        float score = 0.0f;

        // Prioritize customers with tighter time windows (smaller TW_Width)
        if (instance.TW_Width[customerId] > 0.001f) { 
            score += weightTW * (1.0f / instance.TW_Width[customerId]);
        } else {
            score += weightTW * 1000.0f; // Assign a very high score for extremely tight/zero-width TW
        }

        // Prioritize customers with longer service times
        score += weightServiceTime * instance.serviceTime[customerId];

        // Prioritize customers with higher demand
        score += weightDemand * instance.demand[customerId];

        // Prioritize customers further from the depot (node 0)
        score += weightDistance * instance.distanceMatrix[0][customerId];

        // Add a small random perturbation for stochastic behavior
        score += getRandomFraction(-perturbationRange, perturbationRange);

        scoredCustomers.emplace_back(score, customerId);
    }

    // Sort in descending order of score (highest score/hardest customer first)
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the input customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}