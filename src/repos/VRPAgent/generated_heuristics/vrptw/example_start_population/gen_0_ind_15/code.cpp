#include "AgentDesigned.h"
#include <vector>
#include <unordered_set>
#include <algorithm>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomersToRemove = getRandomNumber(5, 20);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersList.push_back(initialCustomer);

    while (selectedCustomersList.size() < numCustomersToRemove) {
        bool addedNewCustomerInIteration = false;

        int expandFromCustomerIdx = getRandomNumber(0, selectedCustomersList.size() - 1);
        int expandFromCustomer = selectedCustomersList[expandFromCustomerIdx];

        int numNeighborsToConsider = std::min((int)sol.instance.adj[expandFromCustomer].size(), getRandomNumber(3, 10));

        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int potentialNeighbor = sol.instance.adj[expandFromCustomer][i];

            if (potentialNeighbor >= 1 && potentialNeighbor <= sol.instance.numCustomers && 
                selectedCustomersSet.count(potentialNeighbor) == 0) {
                
                selectedCustomersSet.insert(potentialNeighbor);
                selectedCustomersList.push_back(potentialNeighbor);
                addedNewCustomerInIteration = true;
                break;
            }

            if (selectedCustomersList.size() == numCustomersToRemove) {
                break;
            }
        }

        if (!addedNewCustomerInIteration && selectedCustomersList.size() < numCustomersToRemove) {
            int newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(newRandomCustomer) != 0) {
                newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newRandomCustomer);
            selectedCustomersList.push_back(newRandomCustomer);
        }
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = instance.TW_Width[customerId];
        score += getRandomFraction() * 0.001f; 
        
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}