#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <queue> 
#include <algorithm> 
#include <vector> 
#include "Utils.h"

// Constants for customer selection
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 30;
const int NEIGHBOR_CONSIDERATION_LIMIT = 20; // Consider up to N closest neighbors for expansion

// Customer selection heuristic: select_by_llm_1
// This heuristic selects a cluster of customers to remove. It starts with a random seed customer
// and expands outwards by selecting nearby unselected customers. Stochasticity is introduced
// by the initial seed choice, the number of customers to remove, and by randomly picking
// from a limited set of close neighbors during expansion.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::queue<int> customersToExpand;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (sol.instance.numCustomers == 0) {
        return {};
    }
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    if (numCustomersToRemove == 0) {
        return {};
    }

    // 1. Select initial seed customer
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers); 
    selectedCustomers.insert(initialCustomer);
    customersToExpand.push(initialCustomer);

    static thread_local std::mt19937 gen(std::random_device{}()); 

    // 2. Expand the cluster
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (customersToExpand.empty()) {
            // All current candidates exhausted, but not enough customers selected.
            // Pick a new random unselected customer as a new seed to form another small cluster.
            int newSeed = -1;
            int attempts = 0;
            // Limit attempts to prevent infinite loop in sparse cases, though unlikely for large instances
            while (attempts < sol.instance.numCustomers * 2 && newSeed == -1) { 
                int potentialSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(potentialSeed) == selectedCustomers.end()) {
                    newSeed = potentialSeed;
                }
                attempts++;
            }
            if (newSeed == -1) { 
                break; // No unselected customer found (e.g., all customers are already selected)
            }
            selectedCustomers.insert(newSeed);
            customersToExpand.push(newSeed);
        }

        int currentCustomer = customersToExpand.front();
        customersToExpand.pop();

        const std::vector<int>& allNeighbors = sol.instance.adj[currentCustomer];
        std::vector<int> potentialNeighborsToChooseFrom;
        
        // Collect a limited number of closest unselected neighbors
        for (size_t i = 0; i < std::min((size_t)NEIGHBOR_CONSIDERATION_LIMIT, allNeighbors.size()); ++i) {
            int neighbor = allNeighbors[i];
            if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                potentialNeighborsToChooseFrom.push_back(neighbor);
            }
        }
        
        if (!potentialNeighborsToChooseFrom.empty()) {
            // Shuffle to pick a random neighbor from the eligible ones, introducing stochasticity
            std::shuffle(potentialNeighborsToChooseFrom.begin(), potentialNeighborsToChooseFrom.end(), gen);
            int chosenNeighbor = potentialNeighborsToChooseFrom[0]; 
            
            selectedCustomers.insert(chosenNeighbor);
            customersToExpand.push(chosenNeighbor);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Constants for customer ordering
const float RANDOM_SCORE_PERTURBATION_RANGE = 0.05f; // Max perturbation range for score

// Customer ordering heuristic: sort_by_llm_1
// This heuristic sorts the removed customers for reinsertion based on their prize-to-demand ratio.
// Customers with higher ratios are prioritized, as they are likely more profitable.
// Stochasticity is introduced by adding a small random perturbation to the score.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float demand = instance.demand[customer_id];
        
        // Base score: prize-to-demand ratio. Add 1.0f to demand to avoid division by zero and to soften very small demands.
        float score = prize / (demand + 1.0f);

        // Stochastic perturbation: add a random value to break ties and introduce diversity in sorting.
        score += getRandomFractionFast() * RANDOM_SCORE_PERTURBATION_RANGE;
        
        scoredCustomers.push_back({score, customer_id});
    }

    // Sort in descending order of score (higher score first)
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Populate the original customers vector with the sorted IDs
    for (size_t i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}