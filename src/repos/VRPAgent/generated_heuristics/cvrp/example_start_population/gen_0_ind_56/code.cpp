#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <deque>
#include <utility> // For std::pair

// Assuming Utils.h provides getRandomNumber, getRandomFraction
// Assuming Solution.h, Instance.h, Tour.h are available

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;
    std::deque<int> queueForExpansion;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 20;

    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) { // If numCustomersToRemove becomes 0 for some reason, ensure at least one if customers exist
        numCustomersToRemove = 1;
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersVec.push_back(seedCustomer);
    queueForExpansion.push_back(seedCustomer);

    int neighborsToConsider = 7; 

    static thread_local std::mt19937 gen(std::random_device{}());

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (queueForExpansion.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            size_t attempts = 0;
            const size_t maxAttempts = sol.instance.numCustomers * 2; 
            while (selectedCustomersSet.count(newSeed) && attempts < maxAttempts) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (selectedCustomersSet.count(newSeed)) {
                break;
            }
            selectedCustomersSet.insert(newSeed);
            selectedCustomersVec.push_back(newSeed);
            queueForExpansion.push_back(newSeed);
            continue;
        }

        std::uniform_int_distribution<> distrib(0, queueForExpansion.size() - 1);
        int expanderIdx = distrib(gen);
        int currentExpander = queueForExpansion[expanderIdx];
        
        std::vector<int> potentialAdds;
        int adjSize = sol.instance.adj[currentExpander].size();
        int maxNeighbors = std::min(adjSize, neighborsToConsider);

        for (int i = 0; i < maxNeighbors; ++i) {
            int neighbor = sol.instance.adj[currentExpander][i];
            if (neighbor == 0 || selectedCustomersSet.count(neighbor)) {
                continue;
            }
            potentialAdds.push_back(neighbor);
        }

        if (!potentialAdds.empty()) {
            std::uniform_int_distribution<> potentialDist(0, potentialAdds.size() - 1);
            int customerToAdd = potentialAdds[potentialDist(gen)];

            selectedCustomersSet.insert(customerToAdd);
            selectedCustomersVec.push_back(customerToAdd);
            queueForExpansion.push_back(customerToAdd);
        } else {
            if (expanderIdx != queueForExpansion.size() - 1) {
                std::swap(queueForExpansion[expanderIdx], queueForExpansion.back());
            }
            queueForExpansion.pop_back();
        }
    }

    return selectedCustomersVec;
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = (float)(instance.demand[customerId] + 1) + instance.distanceMatrix[0][customerId];
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    float pStochasticSwap = 0.2f;

    for (size_t i = 0; i < customerScores.size() - 1; ++i) {
        if (getRandomFraction() < pStochasticSwap) {
            std::swap(customerScores[i], customerScores[i+1]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}