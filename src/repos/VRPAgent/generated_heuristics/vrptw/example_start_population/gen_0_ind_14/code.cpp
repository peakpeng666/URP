#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateSources;

    int numCustomersToRemove = getRandomNumber(10, 25);
    numCustomersToRemove = std::min(numCustomersToRemove, static_cast<int>(0.05 * sol.instance.numCustomers));
    numCustomersToRemove = std::max(numCustomersToRemove, 10);

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    candidateSources.push_back(initialSeedCustomer);

    const int K_NEIGHBORS_POOL = 10; 

    while (selectedCustomersSet.size() < numCustomersToRemove && !candidateSources.empty()) {
        int pivotCustomerIdx = getRandomNumber(0, static_cast<int>(candidateSources.size() - 1));
        int pivotCustomer = candidateSources[pivotCustomerIdx];

        std::vector<int> availableNeighbors;
        const auto& neighbors = sol.instance.adj[pivotCustomer];
        
        for (int i = 0; i < neighbors.size() && i < K_NEIGHBORS_POOL; ++i) {
            int currentNeighbor = neighbors[i];
            if (currentNeighbor != 0 && selectedCustomersSet.find(currentNeighbor) == selectedCustomersSet.end()) {
                availableNeighbors.push_back(currentNeighbor);
            }
        }

        if (!availableNeighbors.empty()) {
            int chosenNeighborIdx = getRandomNumber(0, static_cast<int>(availableNeighbors.size() - 1));
            int chosenNeighbor = availableNeighbors[chosenNeighborIdx];
            
            selectedCustomersSet.insert(chosenNeighbor);
            candidateSources.push_back(chosenNeighbor);
        } else {
            if (candidateSources.size() > 1) {
                std::swap(candidateSources[pivotCustomerIdx], candidateSources.back());
            }
            candidateSources.pop_back();
        }
    }
    
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    const float PERTURBATION_FACTOR = 0.01f;

    for (int customer_id : customers) {
        float score = instance.startTW[customer_id] + getRandomFractionFast() * PERTURBATION_FACTOR;
        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}