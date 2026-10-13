#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int customersToSelectCount = getRandomNumber(10, 20);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateSeeds;
    std::vector<bool> isCustomerSelected(sol.instance.numCustomers + 1, false);

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    isCustomerSelected[initialCustomer] = true;
    candidateSeeds.push_back(initialCustomer);

    while (selectedCustomersSet.size() < customersToSelectCount) {
        if (candidateSeeds.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (isCustomerSelected[newSeed]) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newSeed);
            isCustomerSelected[newSeed] = true;
            candidateSeeds.push_back(newSeed);
            if (selectedCustomersSet.size() == customersToSelectCount) {
                break;
            }
        }

        int currentCustomerIdx = getRandomNumber(0, candidateSeeds.size() - 1);
        int currentCustomer = candidateSeeds[currentCustomerIdx];
        std::swap(candidateSeeds[currentCustomerIdx], candidateSeeds.back());
        candidateSeeds.pop_back();

        int numNeighborsToConsider = std::min((int)sol.instance.adj[currentCustomer].size(), 8);

        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[currentCustomer][i];
            if (!isCustomerSelected[neighbor]) {
                selectedCustomersSet.insert(neighbor);
                isCustomerSelected[neighbor] = true;
                candidateSeeds.push_back(neighbor);
                if (selectedCustomersSet.size() == customersToSelectCount) {
                    goto end_selection_loop;
                }
            }
        }
    }

end_selection_loop:;
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = 0.0f;

        score += (1.0f / (instance.TW_Width[customerId] + 0.001f));

        score += instance.demand[customerId] * 0.1f; 

        score += instance.distanceMatrix[0][customerId] * 0.01f;

        score += getRandomFractionFast() * 0.0001f; 

        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}