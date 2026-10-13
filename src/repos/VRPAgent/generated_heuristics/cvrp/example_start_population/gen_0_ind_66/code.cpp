#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>
#include <numeric>

// Step 1: Customer Selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidateCustomers;

    int numCustomersToRemove = getRandomNumber(10, 30);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    } else if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeedCustomer);
    candidateCustomers.push_back(initialSeedCustomer);

    float diffusionProbability = 0.7f;

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidateCustomers.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            while (selectedCustomers.count(newSeed) && attempts < 1000) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (selectedCustomers.count(newSeed)) {
                break;
            }
            selectedCustomers.insert(newSeed);
            candidateCustomers.push_back(newSeed);
            if (selectedCustomers.size() == numCustomersToRemove) break;
        }

        int randIdx = getRandomNumber(0, static_cast<int>(candidateCustomers.size() - 1));
        int currentCustomer = candidateCustomers[randIdx];

        std::swap(candidateCustomers[randIdx], candidateCustomers.back());
        candidateCustomers.pop_back();

        for (int neighborId : sol.instance.adj[currentCustomer]) {
            if (neighborId > 0 && selectedCustomers.find(neighborId) == selectedCustomers.end()) {
                if (getRandomFractionFast() < diffusionProbability) {
                    selectedCustomers.insert(neighborId);
                    candidateCustomers.push_back(neighborId);
                    if (selectedCustomers.size() == numCustomersToRemove) {
                        break;
                    }
                }
            }
        }
        if (selectedCustomers.size() == numCustomersToRemove) {
            break;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Step 3: Customer Ordering
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int strategy_choice = getRandomNumber(0, 3); // 0: demand, 1: distance to depot, 2: centrality, 3: random

    if (strategy_choice == 3) {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = 0.0f;

        if (strategy_choice == 0) {
            score = static_cast<float>(instance.demand[customerId]);
        } else if (strategy_choice == 1) {
            score = instance.distanceMatrix[0][customerId];
        } else if (strategy_choice == 2) {
            float sumDistToOthers = 0.0f;
            if (customers.size() > 1) {
                for (int otherCustomerId : customers) {
                    if (customerId != otherCustomerId) {
                        sumDistToOthers += instance.distanceMatrix[customerId][otherCustomerId];
                    }
                }
            }
            score = 1000.0f / (1.0f + sumDistToOthers);
        }
        
        score += getRandomFractionFast() * 0.001f;

        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.rbegin(), customerScores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}