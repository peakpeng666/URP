#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> 
#include <vector>
#include <numeric> 
#include "Utils.h" 

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateQueue; 

    int numCustomersToRemove = getRandomNumber(10, 25); 

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) { 
        numCustomersToRemove = 1;
    } else if (sol.instance.numCustomers == 0) {
        return {};
    }

    int startCustomer = getRandomNumber(1, sol.instance.numCustomers); 
    selectedCustomersSet.insert(startCustomer);
    candidateQueue.push_back(startCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove && !candidateQueue.empty()) {
        int queue_idx = getRandomNumber(0, candidateQueue.size() - 1);
        int current_customer = candidateQueue[queue_idx];

        if (candidateQueue.size() > 1) {
            std::swap(candidateQueue[queue_idx], candidateQueue.back());
        }
        candidateQueue.pop_back();

        for (int neighbor : sol.instance.adj[current_customer]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) { 
                selectedCustomersSet.insert(neighbor);
                candidateQueue.push_back(neighbor);

                if (selectedCustomersSet.size() == numCustomersToRemove) {
                    break; 
                }
            }
        }
        if (candidateQueue.empty() && selectedCustomersSet.size() < numCustomersToRemove) {
             int new_seed = getRandomNumber(1, sol.instance.numCustomers);
             while (selectedCustomersSet.count(new_seed)) { 
                 new_seed = getRandomNumber(1, sol.instance.numCustomers);
             }
             selectedCustomersSet.insert(new_seed);
             candidateQueue.push_back(new_seed);
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());

    float random_sort_choice = getRandomFractionFast();

    if (random_sort_choice < 0.33f) {
        std::shuffle(customers.begin(), customers.end(), gen);
    } else if (random_sort_choice < 0.66f) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
        });
    } else {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] > instance.demand[b];
        });
    }
}