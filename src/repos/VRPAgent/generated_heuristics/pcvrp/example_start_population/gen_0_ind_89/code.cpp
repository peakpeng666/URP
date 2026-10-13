#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include "Utils.h"

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateExpansionPool;

    int numCustomersTotal = sol.instance.numCustomers;
    int numCustomersToRemove = getRandomNumber(std::max(5, (int)(numCustomersTotal * 0.02)), 
                                               std::min(30, (int)(numCustomersTotal * 0.05)));
    numCustomersToRemove = std::max(1, numCustomersToRemove);

    int current_seed_customer_idx = getRandomNumber(1, numCustomersTotal);
    selectedCustomersSet.insert(current_seed_customer_idx);
    
    int neighbors_to_add_per_step = getRandomNumber(5, 10); 
    
    for (int neighbor_node_idx : sol.instance.adj[current_seed_customer_idx]) {
        if (neighbor_node_idx == 0) continue;
        if (selectedCustomersSet.find(neighbor_node_idx) == selectedCustomersSet.end()) {
            candidateExpansionPool.push_back(neighbor_node_idx);
        }
        if (candidateExpansionPool.size() >= neighbors_to_add_per_step) break;
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidateExpansionPool.empty()) {
            int new_seed_customer_idx = -1;
            
            int start_idx = getRandomNumber(1, numCustomersTotal); 
            for (int i = 0; i < numCustomersTotal; ++i) {
                int customer_id = 1 + (start_idx + i - 1) % numCustomersTotal; 
                if (selectedCustomersSet.find(customer_id) == selectedCustomersSet.end()) {
                    new_seed_customer_idx = customer_id;
                    break; 
                }
            }

            if (new_seed_customer_idx == -1) {
                break; 
            }
            selectedCustomersSet.insert(new_seed_customer_idx);
            current_seed_customer_idx = new_seed_customer_idx;

            for (int neighbor_node_idx : sol.instance.adj[current_seed_customer_idx]) {
                if (neighbor_node_idx == 0) continue; 
                if (selectedCustomersSet.find(neighbor_node_idx) == selectedCustomersSet.end()) {
                    candidateExpansionPool.push_back(neighbor_node_idx);
                }
            }
        } else {
            int pick_idx = getRandomNumber(0, candidateExpansionPool.size() - 1);
            int customer_to_add = candidateExpansionPool[pick_idx];

            candidateExpansionPool[pick_idx] = candidateExpansionPool.back();
            candidateExpansionPool.pop_back();

            if (selectedCustomersSet.find(customer_to_add) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(customer_to_add);
                current_seed_customer_idx = customer_to_add;

                for (int neighbor_node_idx : sol.instance.adj[current_seed_customer_idx]) {
                    if (neighbor_node_idx == 0) continue;
                    if (selectedCustomersSet.find(neighbor_node_idx) == selectedCustomersSet.end()) {
                        candidateExpansionPool.push_back(neighbor_node_idx);
                    }
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Ordering of the removed customers heuristic
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());
    
    float rand_val = getRandomFractionFast(); 

    if (rand_val < 0.15) { 
        std::shuffle(customers.begin(), customers.end(), gen);
    } else if (rand_val < 0.75) { 
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.prizes[a] > instance.prizes[b];
        });
    } else { 
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] < instance.demand[b];
        });
    }
}