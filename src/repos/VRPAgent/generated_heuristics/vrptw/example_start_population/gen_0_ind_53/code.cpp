#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedSet;
    std::vector<int> selectedList;

    int numCustomersToRemove = getRandomNumber(
        static_cast<int>(sol.instance.numCustomers * 0.02),
        static_cast<int>(sol.instance.numCustomers * 0.06)
    );
    if (numCustomersToRemove < 10) numCustomersToRemove = 10;
    if (numCustomersToRemove > 30) numCustomersToRemove = 30;

    float probNewSeed = 0.25; 

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedSet.insert(initialCustomer);
    selectedList.push_back(initialCustomer);

    while (selectedSet.size() < numCustomersToRemove) {
        if (getRandomFraction() < probNewSeed) {
            int newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedSet.find(newSeedCustomer) == selectedSet.end()) {
                selectedSet.insert(newSeedCustomer);
                selectedList.push_back(newSeedCustomer);
            }
        } else {
            if (selectedList.empty()) {
                continue;
            }
            int pivotCustomerIdx = getRandomNumber(0, selectedList.size() - 1);
            int pivotCustomer = selectedList[pivotCustomerIdx];
            
            int numNeighborsToCheck = std::min((int)sol.instance.adj[pivotCustomer].size(), 10); 
            bool addedNeighbor = false;
            for (int i = 0; i < numNeighborsToCheck; ++i) {
                int neighbor = sol.instance.adj[pivotCustomer][i];
                if (selectedSet.find(neighbor) == selectedSet.end()) {
                    selectedSet.insert(neighbor);
                    selectedList.push_back(neighbor);
                    addedNeighbor = true;
                    break;
                }
            }
        }
    }

    return selectedList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float r = getRandomFraction();

    if (r < 0.35) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.TW_Width[a] < instance.TW_Width[b];
        });
    } else if (r < 0.70) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] > instance.demand[b];
        });
    } else if (r < 0.90) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] > instance.distanceMatrix[0][b];
        });
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}