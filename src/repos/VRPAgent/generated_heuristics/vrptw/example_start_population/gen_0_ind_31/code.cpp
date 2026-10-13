#include "AgentDesigned.h" // Assuming this includes Solution.h, Instance.h, Tour.h, and Utils.h
#include <random>           // For std::mt19937, std::random_device, std::shuffle
#include <unordered_set>    // For std::unordered_set
#include <vector>           // For std::vector
#include <algorithm>        // For std::sort, std::min, std::swap

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(15, 40);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentClusterFrontier;

    static thread_local std::mt19937 gen(std::random_device{}());

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);

    int maxNeighborsToConsider = std::min((int)sol.instance.adj[initialSeedCustomer].size(), 10);
    for (int i = 0; i < maxNeighborsToConsider; ++i) {
        int neighbor_id = sol.instance.adj[initialSeedCustomer][i];
        if (neighbor_id != 0 && selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
            currentClusterFrontier.push_back(neighbor_id);
        }
    }
    std::shuffle(currentClusterFrontier.begin(), currentClusterFrontier.end(), gen);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (currentClusterFrontier.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(newSeed)) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(newSeed);
            maxNeighborsToConsider = std::min((int)sol.instance.adj[newSeed].size(), 10);
            for (int i = 0; i < maxNeighborsToConsider; ++i) {
                int neighbor_id = sol.instance.adj[newSeed][i];
                if (neighbor_id != 0 && selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                    currentClusterFrontier.push_back(neighbor_id);
                }
            }
            std::shuffle(currentClusterFrontier.begin(), currentClusterFrontier.end(), gen);
            if (selectedCustomersSet.size() >= numCustomersToRemove) break;
        }

        int pickedCustomerIdxInFrontier = getRandomNumber(0, currentClusterFrontier.size() - 1);
        int customerToAdd = currentClusterFrontier[pickedCustomerIdxInFrontier];

        currentClusterFrontier[pickedCustomerIdxInFrontier] = currentClusterFrontier.back();
        currentClusterFrontier.pop_back();

        if (selectedCustomersSet.find(customerToAdd) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(customerToAdd);

            maxNeighborsToConsider = std::min((int)sol.instance.adj[customerToAdd].size(), 10);
            for (int i = 0; i < maxNeighborsToConsider; ++i) {
                int neighbor_id = sol.instance.adj[customerToAdd][i];
                if (neighbor_id != 0 && selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                    currentClusterFrontier.push_back(neighbor_id);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.TW_Width[customer_id];
        score += instance.serviceTime[customer_id] * 0.1f;
        score += instance.distanceMatrix[0][customer_id] * 0.001f; 
        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end());

    static thread_local std::mt19937 gen(std::random_device{}());

    for (size_t i = 0; i + 1 < customerScores.size(); ++i) {
        if (getRandomFractionFast() < 0.1f) { 
            std::swap(customerScores[i], customerScores[i+1]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}