#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::unordered_set<int> candidateCustomersSet;

    int numCustomersToRemove = getRandomNumber(sol.instance.numCustomers / 50, sol.instance.numCustomers / 25);
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    } else if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);

    int neighborsToExplore = std::min((int)sol.instance.adj[initialCustomer].size(), 15);
    for (int i = 0; i < neighborsToExplore; ++i) {
        int neighbor = sol.instance.adj[initialCustomer][i];
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            candidateCustomersSet.insert(neighbor);
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidateCustomersSet.empty()) {
            int newCustomer = -1;
            int attempts = 0;
            while (attempts < sol.instance.numCustomers * 2) { 
                int randCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(randCustomer) == selectedCustomersSet.end()) {
                    newCustomer = randCustomer;
                    break;
                }
                attempts++;
            }
            if (newCustomer != -1) {
                selectedCustomersSet.insert(newCustomer);
                neighborsToExplore = std::min((int)sol.instance.adj[newCustomer].size(), 15);
                for (int i = 0; i < neighborsToExplore; ++i) {
                    int neighbor = sol.instance.adj[newCustomer][i];
                    if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                        candidateCustomersSet.insert(neighbor);
                    }
                }
            } else {
                break; 
            }
        } else {
            std::vector<std::pair<int, int>> scoredCandidates; 
            for (int candidate : candidateCustomersSet) {
                int connectivityScore = 0;
                int neighborCheckLimit = std::min((int)sol.instance.adj[candidate].size(), 10);
                for (int i = 0; i < neighborCheckLimit; ++i) {
                    int neighbor = sol.instance.adj[candidate][i];
                    if (selectedCustomersSet.find(neighbor) != selectedCustomersSet.end()) {
                        connectivityScore++;
                    }
                }
                scoredCandidates.push_back({connectivityScore, candidate});
            }

            std::sort(scoredCandidates.rbegin(), scoredCandidates.rend());

            int selectionPoolSize = std::min((int)scoredCandidates.size(), 10); 
            if (selectionPoolSize == 0 && !scoredCandidates.empty()) selectionPoolSize = 1;
            
            int selectedIdx = 0;
            if (selectionPoolSize > 1) {
                selectedIdx = getRandomNumber(0, selectionPoolSize - 1);
            }
            
            int customerToAdd = scoredCandidates[selectedIdx].second;

            selectedCustomersSet.insert(customerToAdd);
            candidateCustomersSet.erase(customerToAdd);

            neighborsToExplore = std::min((int)sol.instance.adj[customerToAdd].size(), 15);
            for (int i = 0; i < neighborsToExplore; ++i) {
                int neighbor = sol.instance.adj[customerToAdd][i];
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    candidateCustomersSet.insert(neighbor);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers; 

    for (int customer_id : customers) {
        float score = (float)instance.demand[customer_id];

        float closestNeighborDistance = 0.0f;
        if (!instance.adj[customer_id].empty()) {
            int closest_neighbor_id = instance.adj[customer_id][0];
            closestNeighborDistance = instance.distanceMatrix[customer_id][closest_neighbor_id];
        } else {
            closestNeighborDistance = 100000.0f; 
        }

        score += 1.0f * closestNeighborDistance; 

        score += getRandomFraction(-0.005f, 0.005f); 

        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.rbegin(), scoredCustomers.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}