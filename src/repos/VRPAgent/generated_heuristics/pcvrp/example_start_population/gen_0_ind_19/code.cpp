#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomers = sol.instance.numCustomers;

    int numCustomersToRemove = getRandomNumber(10, 30);

    int numSeeds = getRandomNumber(2, 5);
    for (int i = 0; i < numSeeds; ++i) {
        int randomCustomer = getRandomNumber(1, numCustomers);
        selectedCustomers.insert(randomCustomer);
    }

    std::vector<int> currentCandidates(selectedCustomers.begin(), selectedCustomers.end());
    int candidateIdx = 0;

    while (selectedCustomers.size() < numCustomersToRemove && candidateIdx < currentCandidates.size()) {
        int focusCustomer = currentCandidates[candidateIdx];
        
        if (focusCustomer >= 1 && focusCustomer <= numCustomers && !sol.instance.adj[focusCustomer].empty()) {
            int neighborsToConsider = std::min((int)sol.instance.adj[focusCustomer].size(), getRandomNumber(3, 7));
            for (int i = 0; i < neighborsToConsider; ++i) {
                int neighborNode = sol.instance.adj[focusCustomer][i];
                
                if (neighborNode >= 1 && neighborNode <= numCustomers) {
                    if (getRandomFraction() < 0.8f) { 
                        if (selectedCustomers.insert(neighborNode).second) {
                            currentCandidates.push_back(neighborNode); 
                        }
                    }
                }
                if (selectedCustomers.size() >= numCustomersToRemove) break;
            }
        }
        candidateIdx++;

        if (candidateIdx >= currentCandidates.size() && selectedCustomers.size() < numCustomersToRemove) {
             int randomCustomer = getRandomNumber(1, numCustomers);
             if (selectedCustomers.insert(randomCustomer).second) {
                 currentCandidates.push_back(randomCustomer);
             }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, numCustomers);
        selectedCustomers.insert(randomCustomer);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());
    std::uniform_real_distribution<float> dist(-0.1f, 0.1f);

    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        float score1 = instance.prizes[c1];
        float score2 = instance.prizes[c2];

        score1 += dist(gen);
        score2 += dist(gen);

        if (score1 != score2) {
            return score1 > score2; 
        } else {
            return instance.distanceMatrix[c1][0] < instance.distanceMatrix[c2][0];
        }
    });
}