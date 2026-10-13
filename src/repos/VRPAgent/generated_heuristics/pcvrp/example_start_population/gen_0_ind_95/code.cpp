#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector> 
#include <algorithm> 
#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 30; 
const int MAX_NEIGHBORS_TO_CONSIDER_FOR_CANDIDATES = 10; 
const int MAX_CANDIDATE_POOL_SIZE = 150; 
const int MAX_RANDOM_SEED_ATTEMPTS = 50; 

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateNeighbors; 

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);

    int neighborsAddedCount = 0;
    for (int neighbor : sol.instance.adj[seedCustomer]) {
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            candidateNeighbors.push_back(neighbor);
            neighborsAddedCount++;
            if (neighborsAddedCount >= MAX_NEIGHBORS_TO_CONSIDER_FOR_CANDIDATES || candidateNeighbors.size() >= MAX_CANDIDATE_POOL_SIZE) {
                break;
            }
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidateNeighbors.empty()) {
            int newSeed = -1;
            for (int i = 0; i < MAX_RANDOM_SEED_ATTEMPTS; ++i) {
                int potentialNewSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potentialNewSeed) == selectedCustomersSet.end()) {
                    newSeed = potentialNewSeed;
                    break;
                }
            }
            if (newSeed == -1) { 
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                        newSeed = i;
                        break;
                    }
                }
            }
            
            if (newSeed == -1) break; 

            selectedCustomersSet.insert(newSeed);
            if (selectedCustomersSet.size() == numCustomersToRemove) break;

            neighborsAddedCount = 0;
            for (int neighbor : sol.instance.adj[newSeed]) {
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    candidateNeighbors.push_back(neighbor);
                    neighborsAddedCount++;
                    if (neighborsAddedCount >= MAX_NEIGHBORS_TO_CONSIDER_FOR_CANDIDATES || candidateNeighbors.size() >= MAX_CANDIDATE_POOL_SIZE) {
                        break;
                    }
                }
            }
            continue; 
        }

        int randomIndex = getRandomNumber(0, candidateNeighbors.size() - 1);
        int customerToSelect = candidateNeighbors[randomIndex];

        std::swap(candidateNeighbors[randomIndex], candidateNeighbors.back());
        candidateNeighbors.pop_back();

        if (selectedCustomersSet.find(customerToSelect) != selectedCustomersSet.end()) {
            continue; 
        }

        selectedCustomersSet.insert(customerToSelect);

        neighborsAddedCount = 0;
        for (int neighbor : sol.instance.adj[customerToSelect]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                candidateNeighbors.push_back(neighbor);
                neighborsAddedCount++;
                if (neighborsAddedCount >= MAX_NEIGHBORS_TO_CONSIDER_FOR_CANDIDATES || candidateNeighbors.size() >= MAX_CANDIDATE_POOL_SIZE) {
                    break;
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.size() <= 1) {
        return;
    }

    float r = getRandomFractionFast(); 

    if (r < 0.6) { 
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    } else if (r < 0.8) { 
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.prizes[a] > instance.prizes[b];
        });
    } else { 
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            float ratio_a = (instance.demand[a] == 0) ? instance.prizes[a] : instance.prizes[a] / static_cast<float>(instance.demand[a]);
            float ratio_b = (instance.demand[b] == 0) ? instance.prizes[b] : instance.prizes[b] / static_cast<float>(instance.demand[b]);
            
            bool a_has_inf_ratio = (instance.demand[a] == 0 && instance.prizes[a] > 0);
            bool b_has_inf_ratio = (instance.demand[b] == 0 && instance.prizes[b] > 0);

            if (a_has_inf_ratio && !b_has_inf_ratio) return true;
            if (!a_has_inf_ratio && b_has_inf_ratio) return false;
            
            return ratio_a > ratio_b;
        });
    }
}