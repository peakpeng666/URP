#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::min and std::sort
#include <vector> // Already included by AgentDesigned.h indirectly, but explicit is good
#include <cmath> // For std::min
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> expansionPool;

    int numCustomersToRemove = getRandomNumber(15, 30);
    if (sol.instance.numCustomers < numCustomersToRemove) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    expansionPool.push_back(initialCustomer);

    int currentPoolIdx = 0;
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (currentPoolIdx >= expansionPool.size()) {
            int newSeedCustomer;
            int attempts = 0;
            while (selectedCustomersSet.size() < sol.instance.numCustomers && attempts < 100) {
                newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(newSeedCustomer) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(newSeedCustomer);
                    expansionPool.push_back(newSeedCustomer);
                    currentPoolIdx = expansionPool.size() - 1;
                    break;
                }
                attempts++;
            }
            if (attempts == 100) {
                break;
            }
            if (selectedCustomersSet.size() == numCustomersToRemove) break;
        }

        int currentCustomer = expansionPool[currentPoolIdx];
        currentPoolIdx++;

        const std::vector<int>& neighbors = sol.instance.adj[currentCustomer];
        int neighborsToConsider = std::min((int)neighbors.size(), 10);

        for (int i = 0; i < neighborsToConsider; ++i) {
            int neighbor = neighbors[i];
            if (neighbor == 0) continue;

            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                float prob_add = 1.0f - (float)i / (neighborsToConsider * 1.5f);
                if (getRandomFractionFast() < prob_add) {
                    selectedCustomersSet.insert(neighbor);
                    expansionPool.push_back(neighbor);
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        goto end_selection_loop;
                    }
                }
            }
        }
    }

end_selection_loop:;

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;

    const float C_DEMAND = 1.0f;
    const float C_DIST_DEPOT = 0.5f;
    const float C_NEIGHBOR_DIST = 0.3f;
    const int K_NEIGHBORS_FOR_AVG = 5;

    for (int customer : customers) {
        float score = 0.0f;

        score += C_DEMAND * instance.demand[customer];

        score += C_DIST_DEPOT * instance.distanceMatrix[0][customer];

        int neighbors_found = 0;
        float sum_neighbor_dist = 0.0f;
        const std::vector<int>& adj_list_for_customer = instance.adj[customer];

        for (int neighbor_node_idx : adj_list_for_customer) {
            if (neighbor_node_idx == 0) continue;
            if (neighbors_found >= K_NEIGHBORS_FOR_AVG) break;
            
            sum_neighbor_dist += instance.distanceMatrix[customer][neighbor_node_idx];
            neighbors_found++;
        }
        
        if (neighbors_found > 0) {
            score += C_NEIGHBOR_DIST * (sum_neighbor_dist / neighbors_found);
        } else {
            score += C_NEIGHBOR_DIST * 1000.0f; 
        }
        scoredCustomers.push_back({score, customer});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}