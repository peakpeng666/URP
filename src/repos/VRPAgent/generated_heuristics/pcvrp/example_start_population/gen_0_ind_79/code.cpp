#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentExpandCandidates;

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    currentExpandCandidates.push_back(initialSeedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (currentExpandCandidates.empty()) {
            int fallbackSeed = -1;
            int attempts = 0;
            const int maxAttempts = 1000;
            while (attempts < maxAttempts) {
                int potentialCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potentialCustomer) == selectedCustomersSet.end()) {
                    fallbackSeed = potentialCustomer;
                    break;
                }
                attempts++;
            }
            if (fallbackSeed != -1) {
                selectedCustomersSet.insert(fallbackSeed);
                currentExpandCandidates.push_back(fallbackSeed);
            } else {
                break;
            }
        }

        int pivotCustomerIdxInList = getRandomNumber(0, currentExpandCandidates.size() - 1);
        int pivotCustomer = currentExpandCandidates[pivotCustomerIdxInList];

        int numNeighborsToConsider = getRandomNumber(1, std::min((int)sol.instance.adj[pivotCustomer].size(), 10));

        std::vector<int> neighborsToShuffle;
        for(int i = 0; i < numNeighborsToConsider; ++i) {
            neighborsToShuffle.push_back(sol.instance.adj[pivotCustomer][i]);
        }
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(neighborsToShuffle.begin(), neighborsToShuffle.end(), gen);

        for (int neighbor : neighborsToShuffle) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(neighbor);
                currentExpandCandidates.push_back(neighbor);
                if (selectedCustomersSet.size() == numCustomersToRemove) {
                    break;
                }
            }
        }
        
        currentExpandCandidates.erase(currentExpandCandidates.begin() + pivotCustomerIdxInList);
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float prize = instance.prizes[customerId];
        float distToDepot = instance.distanceMatrix[0][customerId];

        float score = prize * 100.0f;

        if (std::fabs(distToDepot) > 0.001f) {
            score += 1.0f / distToDepot;
        } else {
            score += 1000.0f;
        }

        score *= getRandomFraction(0.9f, 1.1f);

        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}