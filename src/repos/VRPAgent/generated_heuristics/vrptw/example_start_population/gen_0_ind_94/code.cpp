#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 30);

    int num_seeds = getRandomNumber(1, 3);
    for (int i = 0; i < num_seeds; ++i) {
        int seed = getRandomNumber(1, sol.instance.numCustomers);
        while (selectedCustomers.count(seed)) {
            seed = getRandomNumber(1, sol.instance.numCustomers);
        }
        selectedCustomers.insert(seed);
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> currentCandidatePoolVec;
        std::unordered_set<int> currentCandidatePoolSet;

        for (int c : selectedCustomers) {
            for (int neighbor : sol.instance.adj[c]) {
                if (neighbor > 0 && !selectedCustomers.count(neighbor) && currentCandidatePoolSet.find(neighbor) == currentCandidatePoolSet.end()) {
                    currentCandidatePoolVec.push_back(neighbor);
                    currentCandidatePoolSet.insert(neighbor);
                }
            }
        }

        if (currentCandidatePoolVec.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.count(newSeed)) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(newSeed);
            continue;
        }

        int chosenCandidate = -1;
        float bestScore = -1.0f;
        
        int num_sample_candidates = std::min((int)currentCandidatePoolVec.size(), 10); 

        for (int i = 0; i < num_sample_candidates; ++i) {
            int idx = getRandomNumber(0, currentCandidatePoolVec.size() - 1);
            int candidate = currentCandidatePoolVec[idx];
            
            float score = (1.0f / (sol.instance.TW_Width[candidate] + 0.001f)) + (sol.instance.serviceTime[candidate] / 100.0f);
            
            if (score > bestScore) {
                bestScore = score;
                chosenCandidate = candidate;
            }
        }

        if (chosenCandidate == -1) {
            chosenCandidate = currentCandidatePoolVec[getRandomNumber(0, currentCandidatePoolVec.size() - 1)];
        }
        
        selectedCustomers.insert(chosenCandidate);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customer_id : customers) {
        float score = (1.0f / (instance.TW_Width[customer_id] + 0.001f)) + 
                      (instance.serviceTime[customer_id] / 100.0f) + 
                      (instance.demand[customer_id] / 100.0f);
        
        score += getRandomFractionFast() * 0.5f; 
        
        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}