#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(15, 30); 

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesForExpansion;

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    candidatesForExpansion.push_back(seedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        float expandProbability = 0.85f; 

        bool expanded = false;
        if (!candidatesForExpansion.empty() && getRandomFractionFast() < expandProbability) {
            int pivotIdx = getRandomNumber(0, candidatesForExpansion.size() - 1);
            int pivotCustomer = candidatesForExpansion[pivotIdx];

            for (int neighbor : sol.instance.adj[pivotCustomer]) {
                if (neighbor != 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(neighbor);
                    candidatesForExpansion.push_back(neighbor);
                    expanded = true;
                    break;
                }
            }
        }

        if (!expanded) {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            int safety_counter = 0;
            while (selectedCustomersSet.find(randomCustomer) != selectedCustomersSet.end() && safety_counter < sol.instance.numCustomers * 2) {
                randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter++;
            }
            if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(randomCustomer);
                candidatesForExpansion.push_back(randomCustomer);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    int criteriaType = getRandomNumber(0, 4);

    for (int customerId : customers) {
        float score = 0.0f;
        switch (criteriaType) {
            case 0:
                score = instance.prizes[customerId];
                break;
            case 1:
                score = -instance.distanceMatrix[0][customerId]; 
                break;
            case 2:
                score = -static_cast<float>(instance.demand[customerId]);
                break;
            case 3:
                score = static_cast<float>(instance.adj[customerId].size());
                break;
            default:
                score = getRandomFractionFast();
                break;
        }
        
        score += getRandomFractionFast() * 0.001f; 

        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.rbegin(), customerScores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}