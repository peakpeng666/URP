#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = std::max(5, std::min(20, static_cast<int>(sol.instance.numCustomers * getRandomFraction(0.01f, 0.04f))));

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    std::vector<int> servedCustomers;
    servedCustomers.reserve(sol.instance.numCustomers);
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            servedCustomers.push_back(i);
        }
    }

    if (servedCustomers.empty() && sol.instance.numCustomers > 0) {
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            servedCustomers.push_back(i);
        }
    } else if (servedCustomers.empty()) {
        return {};
    }

    int initialSeedCustomer = servedCustomers[getRandomNumber(0, servedCustomers.size() - 1)];
    selectedCustomersSet.insert(initialSeedCustomer);
    selectedCustomersList.push_back(initialSeedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int sourceCustomerIdx = getRandomNumber(0, selectedCustomersList.size() - 1);
        int sourceCustomer = selectedCustomersList[sourceCustomerIdx];

        std::vector<int> potentialNeighbors;
        for (int neighbor : sol.instance.adj[sourceCustomer]) {
            if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && 
                selectedCustomersSet.count(neighbor) == 0 &&
                sol.customerToTourMap[neighbor] != -1) {
                potentialNeighbors.push_back(neighbor);
                if (potentialNeighbors.size() >= 10) break; 
            }
        }

        if (!potentialNeighbors.empty()) {
            int pickIdx = getRandomNumber(0, potentialNeighbors.size() - 1);
            int newCustomer = potentialNeighbors[pickIdx];
            selectedCustomersSet.insert(newCustomer);
            selectedCustomersList.push_back(newCustomer);
        } else {
            bool foundFallback = false;
            std::vector<int> unselectedServedCustomers;
            for (int c : servedCustomers) {
                if (selectedCustomersSet.count(c) == 0) {
                    unselectedServedCustomers.push_back(c);
                }
            }

            if (!unselectedServedCustomers.empty()) {
                int newCustomer = unselectedServedCustomers[getRandomNumber(0, unselectedServedCustomers.size() - 1)];
                selectedCustomersSet.insert(newCustomer);
                selectedCustomersList.push_back(newCustomer);
                foundFallback = true;
            }

            if (!foundFallback) {
                break; 
            }
        }
    }
    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (getRandomFraction() < 0.15f) {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = instance.prizes[customerId] - 0.5f * instance.distanceMatrix[0][customerId];
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.rbegin(), customerScores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}