#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateQueue;

    int numCustomersToRemove = getRandomNumber(15, 30);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    int numSeeds = getRandomNumber(1, 3);
    for (int i = 0; i < numSeeds; ++i) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomersSet.insert(randomCustomer).second) {
            candidateQueue.push_back(randomCustomer);
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove && !candidateQueue.empty()) {
        int randIdx = getRandomNumber(0, candidateQueue.size() - 1);
        int currentCustomer = candidateQueue[randIdx];

        candidateQueue[randIdx] = candidateQueue.back();
        candidateQueue.pop_back();

        const auto& neighbors = sol.instance.adj[currentCustomer];
        int neighborsToProbe = std::min((int)neighbors.size(), getRandomNumber(5, 10));

        for (int i = 0; i < neighborsToProbe; ++i) {
            int neighborNode = neighbors[i];
            if (neighborNode == 0) continue;
            if (neighborNode > sol.instance.numCustomers) continue;

            if (selectedCustomersSet.size() == numCustomersToRemove) {
                break;
            }

            if (getRandomFraction() < 0.75f) {
                if (selectedCustomersSet.insert(neighborNode).second) {
                    candidateQueue.push_back(neighborNode);
                }
            }
        }

        if (candidateQueue.empty() && selectedCustomersSet.size() < numCustomersToRemove) {
            int newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.insert(newSeedCustomer).second) {
                candidateQueue.push_back(newSeedCustomer);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customer_id : customers) {
        float currentPrize = instance.prizes[customer_id];
        float currentDemand = static_cast<float>(instance.demand[customer_id]);
        float distToDepot = instance.distanceMatrix[0][customer_id];

        float score = 0.0f;

        score += currentPrize * getRandomFraction(0.9f, 1.1f);
        score -= distToDepot * getRandomFraction(0.05f, 0.15f);

        float effectiveDemand = std::max(1.0f, currentDemand);
        score += (currentPrize / effectiveDemand) * getRandomFraction(0.1f, 0.3f);

        score += getRandomFractionFast() * 0.0001f;

        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}