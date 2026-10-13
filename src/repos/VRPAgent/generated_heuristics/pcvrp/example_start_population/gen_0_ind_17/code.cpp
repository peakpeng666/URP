#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> expansionCandidates;

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    expansionCandidates.push_back(initialCustomer);

    size_t currentCandidateIdx = 0;
    while (selectedCustomersSet.size() < numCustomersToRemove && currentCandidateIdx < expansionCandidates.size()) {
        int expandFromCustomer = expansionCandidates[currentCandidateIdx++];
        
        int neighborsCheckedCount = 0;
        for (int neighborId : sol.instance.adj[expandFromCustomer]) {
            if (selectedCustomersSet.find(neighborId) == selectedCustomersSet.end()) {
                if (getRandomFractionFast() < 0.7f) {
                    selectedCustomersSet.insert(neighborId);
                    expansionCandidates.push_back(neighborId);
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        break;
                    }
                }
            }
            neighborsCheckedCount++;
            if (neighborsCheckedCount >= 20) {
                break;
            }
        }
        if (selectedCustomersSet.size() == numCustomersToRemove) {
            break;
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int randomNewCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomersSet.find(randomNewCustomer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(randomNewCustomer);
        }
    }

    std::vector<int> selectedCustomersVec(selectedCustomersSet.begin(), selectedCustomersSet.end());
    return selectedCustomersVec;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float prize = instance.prizes[customerId];
        float distToDepot = instance.distanceMatrix[0][customerId];

        float randomNoise = (getRandomFractionFast() - 0.5f) * 20.0f;
        
        float score = prize - 0.5f * distToDepot + randomNoise;
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}