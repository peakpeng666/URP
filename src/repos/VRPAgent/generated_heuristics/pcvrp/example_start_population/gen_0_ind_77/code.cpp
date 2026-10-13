#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort and std::shuffle
#include <utility>   // For std::pair

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::unordered_set<int> candidateSet; 

    int numCustomersToRemove = getRandomNumber(10, 20);

    std::vector<int> visitedCustomers;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            visitedCustomers.push_back(i);
        }
    }

    if (visitedCustomers.empty()) {
        for (int i = 0; i < numCustomersToRemove; ++i) {
            selectedCustomers.insert(getRandomNumber(1, sol.instance.numCustomers));
        }
        return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
    }

    int initialSeedCustomer = visitedCustomers[getRandomNumber(0, visitedCustomers.size() - 1)];
    selectedCustomers.insert(initialSeedCustomer);

    for (int neighbor : sol.instance.adj[initialSeedCustomer]) {
        if (neighbor == 0 || selectedCustomers.count(neighbor)) continue;
        candidateSet.insert(neighbor);
    }

    static thread_local std::mt19937 gen(std::random_device{}());

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidateSet.empty()) {
            int newSeed = -1;
            std::vector<int> potentialSeeds;
            for (int cust_id : visitedCustomers) {
                if (selectedCustomers.find(cust_id) == selectedCustomers.end()) {
                    potentialSeeds.push_back(cust_id);
                }
            }

            if (!potentialSeeds.empty()) {
                newSeed = potentialSeeds[getRandomNumber(0, potentialSeeds.size() - 1)];
            } else {
                int attempts = 0;
                const int maxAttempts = sol.instance.numCustomers * 2;
                do {
                    newSeed = getRandomNumber(1, sol.instance.numCustomers);
                    attempts++;
                } while (selectedCustomers.count(newSeed) && attempts < maxAttempts);
                
                if (selectedCustomers.count(newSeed) && newSeed != -1) {
                    for(int i = 1; i <= sol.instance.numCustomers; ++i) {
                        if (selectedCustomers.find(i) == selectedCustomers.end()) {
                            newSeed = i;
                            break;
                        }
                    }
                }
            }

            if (newSeed == -1 || selectedCustomers.count(newSeed)) {
                break; 
            }

            selectedCustomers.insert(newSeed);
            for (int neighbor : sol.instance.adj[newSeed]) {
                if (neighbor == 0 || selectedCustomers.count(neighbor)) continue;
                candidateSet.insert(neighbor);
            }
            continue;
        }

        std::vector<int> candidatesVec(candidateSet.begin(), candidateSet.end());
        std::shuffle(candidatesVec.begin(), candidatesVec.end(), gen);

        int pickLimit = std::min((int)candidatesVec.size(), 10); 
        int idxToPick = getRandomNumber(0, pickLimit - 1);
        int customerToSelect = candidatesVec[idxToPick];

        selectedCustomers.insert(customerToSelect);
        candidateSet.erase(customerToSelect); 

        for (int neighbor : sol.instance.adj[customerToSelect]) {
            if (neighbor == 0 || selectedCustomers.count(neighbor)) continue;
            candidateSet.insert(neighbor);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id];

        float score = prize - 2.0f * dist_to_depot; 
        
        score += getRandomFraction(-0.5f, 0.5f); 

        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}