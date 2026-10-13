#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec; 
    const Instance& instance = sol.instance;

    int minCustomersToRemove = std::max(2, static_cast<int>(instance.numCustomers * 0.02));
    int maxCustomersToRemove = std::min(instance.numCustomers, static_cast<int>(instance.numCustomers * 0.05));
    
    if (minCustomersToRemove > maxCustomersToRemove) {
        std::swap(minCustomersToRemove, maxCustomersToRemove);
    }
    maxCustomersToRemove = std::min(maxCustomersToRemove, instance.numCustomers / 2);
    minCustomersToRemove = std::min(minCustomersToRemove, maxCustomersToRemove);

    if (instance.numCustomers > 0) {
        minCustomersToRemove = std::max(1, minCustomersToRemove);
        maxCustomersToRemove = std::max(1, maxCustomersToRemove); 
    }

    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);
    if (numCustomersToRemove == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, instance.numCustomers); 
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        int anchorCustomer = selectedCustomersVec[getRandomNumber(0, selectedCustomersVec.size() - 1)];

        bool addedNeighbor = false;
        const std::vector<int>& neighbors = instance.adj[anchorCustomer];

        if (!neighbors.empty()) {
            int startIdx = getRandomNumber(0, neighbors.size() - 1);
            for (size_t i = 0; i < neighbors.size(); ++i) {
                int neighborIdx = (startIdx + i) % neighbors.size();
                int neighbor = neighbors[neighborIdx];

                if (neighbor >= 1 && neighbor <= instance.numCustomers && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(neighbor);
                    selectedCustomersVec.push_back(neighbor);
                    addedNeighbor = true;
                    break;
                }
            }
        }

        if (!addedNeighbor) {
            if (selectedCustomersSet.size() == instance.numCustomers) {
                break;
            }
            int randomUnselectedCustomer = -1;
            int attempts = 0;
            while (attempts < 1000) { 
                int candidateCustomer = getRandomNumber(1, instance.numCustomers);
                if (selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
                    randomUnselectedCustomer = candidateCustomer;
                    break;
                }
                attempts++;
            }
            if (randomUnselectedCustomer != -1) {
                selectedCustomersSet.insert(randomUnselectedCustomer);
                selectedCustomersVec.push_back(randomUnselectedCustomer);
            } else {
                break;
            }
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<int, float>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float distanceToDepot = instance.distanceMatrix[0][customerId]; 
        float randomJitter = (getRandomFractionFast() - 0.5f) * (distanceToDepot * 0.1f);
        float score = distanceToDepot + randomJitter;
        customerScores.push_back({customerId, score});
    }

    if (getRandomFractionFast() < 0.75f) {
        std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<int, float>& a, const std::pair<int, float>& b) {
            return a.second < b.second;
        });
    } else {
        std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<int, float>& a, const std::pair<int, float>& b) {
            return a.second > b.second;
        });
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].first;
    }
}