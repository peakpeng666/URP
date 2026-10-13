#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::shuffle, std::sort, std::min
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateCustomersForExpansion;

    int numCustomersToRemoveMin = 10;
    int numCustomersToRemoveMax = 20;
    int numCustomersToRemove = getRandomNumber(numCustomersToRemoveMin, numCustomersToRemoveMax);

    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    if (numCustomersToRemove == 0) {
        return {};
    }
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    candidateCustomersForExpansion.push_back(initialCustomer);

    const int MAX_NEIGHBORS_TO_CONSIDER = 15;
    const int MAX_EXPANSION_ATTEMPTS_PER_CANDIDATE = 5;

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidateCustomersForExpansion.empty()) {
            int newSeedCustomer = -1;
            int attempts = 0;
            while (newSeedCustomer == -1 || selectedCustomersSet.count(newSeedCustomer)) {
                newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
                if (attempts > sol.instance.numCustomers * 2) {
                    break;
                }
            }
            if (newSeedCustomer != -1 && !selectedCustomersSet.count(newSeedCustomer)) {
                selectedCustomersSet.insert(newSeedCustomer);
                candidateCustomersForExpansion.push_back(newSeedCustomer);
            } else {
                break;
            }
        }

        int currentCustomerIndexInCandidates = getRandomNumber(0, candidateCustomersForExpansion.size() - 1);
        int currentCustomer = candidateCustomersForExpansion[currentCustomerIndexInCandidates];
        
        bool expanded = false;
        for (int attempt = 0; attempt < MAX_EXPANSION_ATTEMPTS_PER_CANDIDATE; ++attempt) {
            if (sol.instance.adj[currentCustomer].empty()) {
                break;
            }
            
            int numAvailableNeighbors = sol.instance.adj[currentCustomer].size();
            int neighborIdxToConsiderLimit = std::min(numAvailableNeighbors, MAX_NEIGHBORS_TO_CONSIDER);
            
            if (neighborIdxToConsiderLimit == 0) {
                break; // No neighbors to consider
            }

            int randomNeighborInAdjListIdx = getRandomNumber(0, neighborIdxToConsiderLimit - 1);
            int potentialNeighbor = sol.instance.adj[currentCustomer][randomNeighborInAdjListIdx];

            if (!selectedCustomersSet.count(potentialNeighbor)) {
                selectedCustomersSet.insert(potentialNeighbor);
                candidateCustomersForExpansion.push_back(potentialNeighbor);
                expanded = true;
                break;
            }
        }

        if (!expanded) {
            candidateCustomersForExpansion.erase(candidateCustomersForExpansion.begin() + currentCustomerIndexInCandidates);
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    enum SortStrategy {
        RANDOM_SORT,
        DEMAND_DESCENDING,
        DISTANCE_TO_DEPOT_ASCENDING,
        NUM_STRATEGIES
    };

    std::vector<float> strategy_weights = {
        0.25f,
        0.50f,
        0.25f
    };

    float total_weight = 0.0f;
    for(float w : strategy_weights) {
        total_weight += w;
    }

    float rand_val = getRandomFractionFast() * total_weight;
    SortStrategy chosenStrategy = RANDOM_SORT;
    float cumulative_weight = 0.0f;
    for (int i = 0; i < NUM_STRATEGIES; ++i) {
        cumulative_weight += strategy_weights[i];
        if (rand_val < cumulative_weight) {
            chosenStrategy = static_cast<SortStrategy>(i);
            break;
        }
    }

    switch (chosenStrategy) {
        case RANDOM_SORT: {
            static thread_local std::mt19937 gen(std::random_device{}());
            std::shuffle(customers.begin(), customers.end(), gen);
            break;
        }
        case DEMAND_DESCENDING: {
            std::sort(customers.begin(), customers.end(), [&](int a, int b) {
                return instance.demand[a] > instance.demand[b];
            });
            break;
        }
        case DISTANCE_TO_DEPOT_ASCENDING: {
            std::sort(customers.begin(), customers.end(), [&](int a, int b) {
                return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
            });
            break;
        }
        default: {
            static thread_local std::mt19937 gen(std::random_device{}());
            std::shuffle(customers.begin(), customers.end(), gen);
            break;
        }
    }
}