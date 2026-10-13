#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>

// Using a thread_local random generator for std::shuffle
static thread_local std::mt19937 shuffle_gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToTarget = getRandomNumber(10, 25); 

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    std::vector<int> expansionCandidates; 

    int initialSeedId = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedId);
    selectedCustomersList.push_back(initialSeedId);
    expansionCandidates.push_back(initialSeedId);

    while (selectedCustomersList.size() < numCustomersToTarget) {
        if (expansionCandidates.empty()) {
            std::vector<int> unselectedCustomers;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                    unselectedCustomers.push_back(i);
                }
            }
            if (unselectedCustomers.empty()) {
                break; 
            }
            int newSeed = unselectedCustomers[getRandomNumber(0, unselectedCustomers.size() - 1)];
            selectedCustomersSet.insert(newSeed);
            selectedCustomersList.push_back(newSeed);
            expansionCandidates.push_back(newSeed);
            
            if (selectedCustomersList.size() == numCustomersToTarget) {
                break;
            }
            continue;
        }

        int randomExpansionIdx = getRandomNumber(0, expansionCandidates.size() - 1);
        int customerToExpandFrom = expansionCandidates[randomExpansionIdx];

        const auto& neighbors = sol.instance.adj[customerToExpandFrom];
        std::vector<int> eligibleNeighbors;
        for (int neighborId : neighbors) {
            if (neighborId > 0 && neighborId <= sol.instance.numCustomers && selectedCustomersSet.find(neighborId) == selectedCustomersSet.end()) {
                eligibleNeighbors.push_back(neighborId);
            }
        }

        if (eligibleNeighbors.empty()) {
            std::swap(expansionCandidates[randomExpansionIdx], expansionCandidates.back());
            expansionCandidates.pop_back();
            continue;
        }

        std::shuffle(eligibleNeighbors.begin(), eligibleNeighbors.end(), shuffle_gen);

        int numToAttemptToAdd = getRandomNumber(1, std::min((int)eligibleNeighbors.size(), 3));
        
        for (int i = 0; i < numToAttemptToAdd; ++i) {
            int neighborToAdd = eligibleNeighbors[i];
            if (selectedCustomersSet.find(neighborToAdd) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(neighborToAdd);
                selectedCustomersList.push_back(neighborToAdd);
                expansionCandidates.push_back(neighborToAdd);
                
                if (selectedCustomersList.size() == numCustomersToTarget) {
                    goto end_selection_loop; 
                }
            }
        }
    }

    end_selection_loop:;

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    float TW_Width_weight = 1000.0f;
    float demand_weight = 0.5f;      
    float dist_weight = 0.01f;       

    for (int customer_id : customers) {
        float score = 0.0f;

        score += TW_Width_weight * instance.TW_Width[customer_id];

        score -= demand_weight * instance.demand[customer_id];

        score -= dist_weight * instance.distanceMatrix[0][customer_id];

        score += getRandomFraction(-0.001f, 0.001f); 

        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first < b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}