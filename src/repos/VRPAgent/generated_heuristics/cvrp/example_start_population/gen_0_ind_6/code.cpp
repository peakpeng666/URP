#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(15, 30);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> resultCustomers;

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    int currentCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(currentCustomer);
    resultCustomers.push_back(currentCustomer);

    for (int i = 1; i < numCustomersToRemove; ++i) {
        bool foundNext = false;
        int expansionSource = resultCustomers[getRandomNumber(0, resultCustomers.size() - 1)];

        const auto& neighbors = sol.instance.adj[expansionSource];

        std::vector<int> candidateNeighbors;
        int numNeighborsToConsider = std::min((int)neighbors.size(), getRandomNumber(5, 10));

        for (int j = 0; j < numNeighborsToConsider; ++j) {
            int neighborNode = neighbors[j];
            if (neighborNode == 0) {
                continue;
            }
            if (selectedCustomersSet.count(neighborNode)) {
                continue;
            }
            candidateNeighbors.push_back(neighborNode);
        }

        if (!candidateNeighbors.empty()) {
            int nextCustomer = candidateNeighbors[getRandomNumber(0, candidateNeighbors.size() - 1)];
            selectedCustomersSet.insert(nextCustomer);
            resultCustomers.push_back(nextCustomer);
            foundNext = true;
        }

        if (!foundNext) {
            int newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(newRandomCustomer)) {
                newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newRandomCustomer);
            resultCustomers.push_back(newRandomCustomer);
        }
    }

    return resultCustomers;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    const float DEMAND_WEIGHT = 0.4f;
    const float DISTANCE_DEPOT_WEIGHT = 0.3f;
    const float NEIGHBOR_COUNT_WEIGHT = 0.2f;
    const float RANDOM_NOISE_FACTOR = 0.1f;

    for (int customer_id : customers) {
        float demand = static_cast<float>(instance.demand[customer_id]);
        float dist_from_depot = instance.distanceMatrix[0][customer_id];
        float num_neighbors = static_cast<float>(instance.adj[customer_id].size());

        float score = (demand * DEMAND_WEIGHT) +
                      (dist_from_depot * DISTANCE_DEPOT_WEIGHT) +
                      (num_neighbors * NEIGHBOR_COUNT_WEIGHT);

        score += getRandomFractionFast() * RANDOM_NOISE_FACTOR;

        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}