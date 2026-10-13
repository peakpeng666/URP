#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <queue>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    std::unordered_set<int> selectedCustomers;
    std::queue<int> customersToExplore;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (instance.numCustomers == 0) {
        return {};
    }
    int initialSeedCustomer = getRandomNumber(1, instance.numCustomers);

    selectedCustomers.insert(initialSeedCustomer);
    customersToExplore.push(initialSeedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove && !customersToExplore.empty()) {
        int currentCustomer = customersToExplore.front();
        customersToExplore.pop();

        int numNeighborsToConsider = getRandomNumber(1, 3);

        for (int i = 0; i < numNeighborsToConsider; ++i) {
            if (i < instance.adj[currentCustomer].size()) {
                int neighbor = instance.adj[currentCustomer][i];

                if (neighbor >= 1 && neighbor <= instance.numCustomers && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    selectedCustomers.insert(neighbor);
                    customersToExplore.push(neighbor);

                    if (selectedCustomers.size() == numCustomersToRemove) {
                        break;
                    }
                }
            } else {
                break;
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, instance.numCustomers);
        selectedCustomers.insert(randomCustomer);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = 0.0f;

        score += 100.0f / (instance.TW_Width[customerId] + 1e-6f);

        score += static_cast<float>(instance.demand[customerId]);

        score += instance.serviceTime[customerId] * 5.0f;

        customerScores.emplace_back(score, customerId);
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }

    int numRandomSwaps = getRandomNumber(0, static_cast<int>(customers.size() / 2));

    for (int i = 0; i < numRandomSwaps; ++i) {
        if (customers.size() < 2) break;
        int idx1 = getRandomNumber(0, static_cast<int>(customers.size() - 1));
        int idx2 = getRandomNumber(0, static_cast<int>(customers.size() - 1));
        std::swap(customers[idx1], customers[idx2]);
    }
}