#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <numeric>   // For std::iota
#include <limits>    // For std::numeric_limits
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> removedCustomersSet;
    std::vector<int> expansionCandidates; // Customers from which we can expand
    const Instance& instance = sol.instance;

    int numCustomersToRemove = getRandomNumber(20, 50); 
    if (numCustomersToRemove > instance.numCustomers) {
        numCustomersToRemove = instance.numCustomers;
    }
    if (numCustomersToRemove == 0) return {};

    int initialSeed = getRandomNumber(1, instance.numCustomers);
    removedCustomersSet.insert(initialSeed);
    expansionCandidates.push_back(initialSeed);

    const float P_ADD_BASE = 0.8f; 
    const float P_ADD_DECREMENT_PER_RANK = 0.1f; 

    while (removedCustomersSet.size() < numCustomersToRemove) {
        if (expansionCandidates.empty()) {
            int newSeed = getRandomNumber(1, instance.numCustomers);
            while (removedCustomersSet.count(newSeed) > 0 && removedCustomersSet.size() < instance.numCustomers) {
                newSeed = getRandomNumber(1, instance.numCustomers);
            }
            if (removedCustomersSet.count(newSeed) > 0 && removedCustomersSet.size() == instance.numCustomers) break;

            removedCustomersSet.insert(newSeed);
            expansionCandidates.push_back(newSeed);
            if (removedCustomersSet.size() >= numCustomersToRemove) break;
        }

        int pivotIndex = getRandomNumber(0, expansionCandidates.size() - 1);
        int pivotCustomer = expansionCandidates[pivotIndex];

        int neighborsAddedFromPivot = 0;
        const int MAX_NEIGHBORS_TO_TRY = 5; 

        for (int i = 0; i < instance.adj[pivotCustomer].size() && i < MAX_NEIGHBORS_TO_TRY; ++i) {
            int neighborId = instance.adj[pivotCustomer][i];

            if (removedCustomersSet.count(neighborId) == 0) { 
                float currentPAdd = P_ADD_BASE - (i * P_ADD_DECREMENT_PER_RANK);
                if (currentPAdd < 0.1f) currentPAdd = 0.1f;

                if (getRandomFractionFast() < currentPAdd) {
                    removedCustomersSet.insert(neighborId);
                    expansionCandidates.push_back(neighborId);
                    neighborsAddedFromPivot++;
                    if (removedCustomersSet.size() >= numCustomersToRemove) break;
                    if (neighborsAddedFromPivot >= 2 && getRandomFractionFast() < 0.5f) break; 
                }
            }
        }
        
        expansionCandidates[pivotIndex] = expansionCandidates.back();
        expansionCandidates.pop_back();
    }

    return std::vector<int>(removedCustomersSet.begin(), removedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());
    
    const float W_TW_TIGHTNESS = 100.0f;
    const float W_DEMAND = 1.0f;
    const float W_SERVICE_TIME = 5.0f;

    float minScore = std::numeric_limits<float>::max();
    float maxScore = std::numeric_limits<float>::lowest();

    for (int customerId : customers) {
        float score = 
            (W_TW_TIGHTNESS / (instance.TW_Width[customerId] + 1.0f)) + 
            (W_DEMAND * static_cast<float>(instance.demand[customerId])) + 
            (W_SERVICE_TIME * instance.serviceTime[customerId]);
        
        scoredCustomers.push_back({score, customerId});

        if (score < minScore) minScore = score;
        if (score > maxScore) maxScore = score;
    }

    float scoreRange = maxScore - minScore;
    if (scoreRange < 1e-6f) scoreRange = 1.0f; 

    const float NOISE_MAGNITUDE_FACTOR = 0.05f; 

    for (auto& p : scoredCustomers) {
        float noise = getRandomFractionFast() * 2.0f - 1.0f; 
        p.first += noise * NOISE_MAGNITUDE_FACTOR * scoreRange;
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}