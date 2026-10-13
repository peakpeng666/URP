#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> potentialClusterSeeds;

    int numCustomersToRemove = getRandomNumber(15, 30);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    int numInitialSeeds = getRandomNumber(1, 3);
    for (int i = 0; i < numInitialSeeds && selectedCustomersSet.size() < numCustomersToRemove; ++i) {
        int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomersSet.find(seedCustomer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(seedCustomer);
            potentialClusterSeeds.push_back(seedCustomer);
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int chosenCustomerIdx;
        if (!potentialClusterSeeds.empty() && getRandomFraction() < 0.8f) {
            chosenCustomerIdx = potentialClusterSeeds[getRandomNumber(0, potentialClusterSeeds.size() - 1)];
        } else {
            chosenCustomerIdx = getRandomNumber(1, sol.instance.numCustomers);
        }

        int numNeighborsToConsider = std::min((int)sol.instance.adj[chosenCustomerIdx].size(), getRandomNumber(3, 8));

        int neighborsAddedInThisStep = 0;
        for (int i = 0; i < numNeighborsToConsider && selectedCustomersSet.size() < numCustomersToRemove; ++i) {
            int neighbor = sol.instance.adj[chosenCustomerIdx][i];

            if (getRandomFraction() < 0.7f) {
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(neighbor);
                    potentialClusterSeeds.push_back(neighbor);
                    neighborsAddedInThisStep++;
                }
            }
        }

        if (neighborsAddedInThisStep == 0 && selectedCustomersSet.find(chosenCustomerIdx) == selectedCustomersSet.end() && selectedCustomersSet.size() < numCustomersToRemove) {
             selectedCustomersSet.insert(chosenCustomerIdx);
             potentialClusterSeeds.push_back(chosenCustomerIdx);
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float w_prize = getRandomFraction(0.8f, 1.2f);
    float w_demand = getRandomFraction(0.1f, 0.5f);
    float w_dist_depot = getRandomFraction(0.01f, 0.05f);

    std::vector<float> scores(customers.size());

    for (size_t i = 0; i < customers.size(); ++i) {
        int customer_id = customers[i];
        scores[i] = (instance.prizes[customer_id] * w_prize) -
                    (instance.demand[customer_id] * w_demand) -
                    (instance.distanceMatrix[0][customer_id] * w_dist_depot) +
                    getRandomFraction(-0.001f, 0.001f);
    }

    std::vector<int> sorted_indices = argsort(scores);

    std::vector<int> temp_customers = customers;

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = temp_customers[sorted_indices[customers.size() - 1 - i]];
    }
}