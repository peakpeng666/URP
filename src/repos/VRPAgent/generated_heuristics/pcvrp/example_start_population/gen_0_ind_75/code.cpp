#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include "Utils.h"
#include <algorithm>
#include <vector>
#include <limits>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selectedCustomers;
    std::unordered_set<int> selectedSet;

    int numCustomersToRemove = getRandomNumber(10, 20); 
    
    int seedCustomer = -1;
    if (getRandomFraction() < 0.7) { 
        std::vector<int> visited_customers;
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (sol.customerToTourMap[i] != -1) {
                visited_customers.push_back(i);
            }
        }
        if (!visited_customers.empty()) {
            seedCustomer = visited_customers[getRandomNumber(0, visited_customers.size() - 1)];
        } else {
            seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
        }
    } else { 
        seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    if (seedCustomer < 1 || seedCustomer > sol.instance.numCustomers) {
        seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }

    selectedCustomers.push_back(seedCustomer);
    selectedSet.insert(seedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> candidatePool;
        for (int customer_id : selectedCustomers) {
            if (customer_id >= 0 && customer_id < sol.instance.adj.size()) {
                const auto& neighbors = sol.instance.adj[customer_id];
                int neighbors_added = 0;
                for (int neighbor : neighbors) {
                    if (selectedSet.find(neighbor) == selectedSet.end()) { 
                        candidatePool.push_back(neighbor);
                    }
                    neighbors_added++;
                    if (neighbors_added >= 5) break; 
                }
            }
        }

        int nextCustomer = -1;
        bool foundNewCustomer = false;

        if (getRandomFraction() < 0.2 || candidatePool.empty()) { 
            int attempts = 0;
            while (attempts < 50) { 
                int potentialCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedSet.find(potentialCustomer) == selectedSet.end()) {
                    nextCustomer = potentialCustomer;
                    foundNewCustomer = true;
                    break;
                }
                attempts++;
            }
        } else { 
            int attempts = 0;
            while (attempts < 50) { 
                int potentialCustomer = candidatePool[getRandomNumber(0, candidatePool.size() - 1)];
                if (selectedSet.find(potentialCustomer) == selectedSet.end()) {
                    nextCustomer = potentialCustomer;
                    foundNewCustomer = true;
                    break;
                }
                attempts++;
            }
        }
        
        if (foundNewCustomer) {
            selectedCustomers.push_back(nextCustomer);
            selectedSet.insert(nextCustomer);
        } else {
            break; 
        }
    }
    return selectedCustomers;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float rand_val = getRandomFraction();

    if (rand_val < 0.4) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.prizes[a] > instance.prizes[b];
        });
    } else if (rand_val < 0.7) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            float ratio_a = (instance.demand[a] > 0) ? instance.prizes[a] / instance.demand[a] : -std::numeric_limits<float>::max();
            float ratio_b = (instance.demand[b] > 0) ? instance.prizes[b] / instance.demand[b] : -std::numeric_limits<float>::max();
            return ratio_a > ratio_b;
        });
    } else if (rand_val < 0.9) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
        });
    } else {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            size_t num_neighbors_a = (a >= 0 && a < instance.adj.size()) ? instance.adj[a].size() : 0;
            size_t num_neighbors_b = (b >= 0 && b < instance.adj.size()) ? instance.adj[b].size() : 0;
            return num_neighbors_a > num_neighbors_b;
        });
    }
}