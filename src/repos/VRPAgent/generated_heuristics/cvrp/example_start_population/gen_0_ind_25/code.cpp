#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidateQueue;

    int numCustomersToRemove = getRandomNumber(10, 20);
    int maxNeighborsToConsider = 5;

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);
    candidateQueue.push_back(seedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int nextCustomer = -1;
        float p = getRandomFractionFast();

        if (p < 0.8f && !candidateQueue.empty()) {
            int anchorIndex = getRandomNumber(0, candidateQueue.size() - 1);
            int anchorCustomer = candidateQueue[anchorIndex];

            for (int i = 0; i < std::min((int)sol.instance.adj[anchorCustomer].size(), maxNeighborsToConsider); ++i) {
                int neighborId = sol.instance.adj[anchorCustomer][i];
                if (neighborId > 0 && selectedCustomers.count(neighborId) == 0) {
                    nextCustomer = neighborId;
                    break;
                }
            }
        }

        if (nextCustomer == -1) {
            int tries = 0;
            const int maxTries = 100;
            while (tries < maxTries) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.count(randomCustomer) == 0) {
                    nextCustomer = randomCustomer;
                    break;
                }
                tries++;
            }
        }

        if (nextCustomer != -1) {
            selectedCustomers.insert(nextCustomer);
            candidateQueue.push_back(nextCustomer);
        } else {
            break;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());
    float p = getRandomFractionFast();

    if (p < 0.7f) {
        std::vector<std::pair<int, int>> scoredCustomers;
        for (int c_id : customers) {
            scoredCustomers.push_back({instance.demand[c_id], c_id});
        }
        std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scoredCustomers[i].second;
        }
    } else if (p < 0.9f) {
        std::vector<std::pair<float, int>> scoredCustomers;
        for (int c_id : customers) {
            scoredCustomers.push_back({instance.distanceMatrix[0][c_id], c_id});
        }
        std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scoredCustomers[i].second;
        }
    } else {
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}