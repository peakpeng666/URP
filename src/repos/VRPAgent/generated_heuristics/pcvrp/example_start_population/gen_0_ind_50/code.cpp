#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

#include "Utils.h" 

namespace {
    static thread_local std::mt19937 gen(std::random_device{}());
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(15, 30); 

    std::vector<int> expansionCandidates; 

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    
    selectedCustomers.insert(initialSeedCustomer);
    expansionCandidates.push_back(initialSeedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (expansionCandidates.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.find(newSeed) != selectedCustomers.end()) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(newSeed);
            expansionCandidates.push_back(newSeed);
        }

        std::shuffle(expansionCandidates.begin(), expansionCandidates.end(), gen);

        int currentExpansionCustomer = expansionCandidates.back();
        expansionCandidates.pop_back(); 

        int numNeighborsToExplore = getRandomNumber(3, 8); 
        int neighborsExplored = 0;

        for (int neighbor : sol.instance.adj[currentExpansionCustomer]) {
            if (neighborsExplored >= numNeighborsToExplore) break; 
            if (selectedCustomers.size() >= numCustomersToRemove) break; 

            if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                selectedCustomers.insert(neighbor);
                expansionCandidates.push_back(neighbor); 
                neighborsExplored++;
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    float prizeCoefficient = 1.0f;          
    float demandPenaltyCoefficient = 0.5f;  
    float distancePenaltyCoefficient = 0.01f; 

    float stochasticMagnitude = 0.05f; 

    for (int customerId : customers) {
        float score = 0.0f;

        score += instance.prizes[customerId] * prizeCoefficient;

        score -= instance.demand[customerId] * demandPenaltyCoefficient;
        
        score -= instance.distanceMatrix[0][customerId] * distancePenaltyCoefficient;

        score += (getRandomFraction(0.0f, 1.0f) * 2.0f - 1.0f) * stochasticMagnitude; 

        scoredCustomers.push_back({score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}