#include "AgentDesigned.h"
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> removedCustomers;
    std::unordered_set<int> removedSet;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove <= 0 || sol.instance.numCustomers == 0) {
        return removedCustomers;
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    removedCustomers.push_back(initialCustomer);
    removedSet.insert(initialCustomer);

    while (removedCustomers.size() < numCustomersToRemove) {
        int focusCustomerIdx = getRandomNumber(0, removedCustomers.size() - 1);
        int focusCustomer = removedCustomers[focusCustomerIdx];

        bool addedNewCustomer = false;
        int numNeighborsToConsider = std::min((int)sol.instance.adj[focusCustomer].size(), 10);

        std::vector<int> candidateNeighbors;
        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[focusCustomer][i];
            if (removedSet.find(neighbor) == removedSet.end()) {
                candidateNeighbors.push_back(neighbor);
            }
        }
        
        if (!candidateNeighbors.empty()) {
            int selectedNeighbor = candidateNeighbors[getRandomNumber(0, candidateNeighbors.size() - 1)];
            removedCustomers.push_back(selectedNeighbor);
            removedSet.insert(selectedNeighbor);
            addedNewCustomer = true;
        }

        if (!addedNewCustomer) {
            int randomCustomerAttempts = 0;
            while (randomCustomerAttempts < 100 && removedCustomers.size() < numCustomersToRemove) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (removedSet.find(randomCustomer) == removedSet.end()) {
                    removedCustomers.push_back(randomCustomer);
                    removedSet.insert(randomCustomer);
                    addedNewCustomer = true;
                    break;
                }
                randomCustomerAttempts++;
            }
            if (!addedNewCustomer) {
                break;
            }
        }
    }
    return removedCustomers;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::sort(customers.begin(), customers.end(), [&](int a, int b) {
        if (instance.startTW[a] != instance.startTW[b]) {
            return instance.startTW[a] < instance.startTW[b];
        }
        return instance.TW_Width[a] < instance.TW_Width[b];
    });

    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFraction(0.0, 1.0) < 0.15) {
            std::swap(customers[i], customers[i + 1]);
        }
    }
}