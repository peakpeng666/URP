#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>

// Customer selection heuristic for LNS
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> customersToRemove;

    const int MIN_CUSTOMERS_TO_REMOVE = 5;
    const int MAX_CUSTOMERS_TO_REMOVE = 15;
    const int NEIGHBOR_SEARCH_LIMIT = 7; 
    const float PROB_START_NEW_CLUSTER = 0.15f; 

    int numCustomersToActuallyRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    std::vector<int> expansionSeeds; 

    while (selectedCustomersSet.size() < numCustomersToActuallyRemove) {
        if (expansionSeeds.empty() || getRandomFractionFast() < PROB_START_NEW_CLUSTER) {
            int newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            int attemptCount = 0;
            while (selectedCustomersSet.count(newSeedCustomer) && attemptCount < 100) { 
                newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attemptCount++;
            }
            if (!selectedCustomersSet.count(newSeedCustomer)) {
                selectedCustomersSet.insert(newSeedCustomer);
                expansionSeeds.push_back(newSeedCustomer);
            } else {
                if (expansionSeeds.empty()) break;
            }
        } else {
            std::vector<int> potentialCandidates;
            for (int currentSeed : expansionSeeds) {
                for (int i = 0; i < std::min((int)sol.instance.adj[currentSeed].size(), NEIGHBOR_SEARCH_LIMIT); ++i) {
                    int neighborId = sol.instance.adj[currentSeed][i];
                    if (!selectedCustomersSet.count(neighborId)) {
                        potentialCandidates.push_back(neighborId);
                    }
                }
            }

            if (!potentialCandidates.empty()) {
                int chosenCandidate = potentialCandidates[getRandomNumber(0, potentialCandidates.size() - 1)];
                selectedCustomersSet.insert(chosenCandidate);
                expansionSeeds.push_back(chosenCandidate);
            } else {
                expansionSeeds.clear();
            }
        }
    }

    customersToRemove.assign(selectedCustomersSet.begin(), selectedCustomersSet.end());
    
    return customersToRemove;
}

// Ordering of the removed customers for reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float WEIGHT_PRIZE = 0.7f; 
    const float WEIGHT_INVERSE_DIST_TO_DEPOT = 0.3f; 
    const float STOCHASTIC_NOISE_FACTOR = 0.05f; 

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float distToDepot = instance.distanceMatrix[0][customer_id];
        distToDepot = std::fmax(distToDepot, 1e-6f);

        float baseScore = WEIGHT_PRIZE * prize + WEIGHT_INVERSE_DIST_TO_DEPOT * (1.0f / distToDepot);
        
        float noise = getRandomFraction(-STOCHASTIC_NOISE_FACTOR, STOCHASTIC_NOISE_FACTOR);
        float finalScore = baseScore * (1.0f + noise);
        
        scoredCustomers.push_back({finalScore, customer_id});
    }

    std::sort(scoredCustomers.rbegin(), scoredCustomers.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}