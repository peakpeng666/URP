#include "AgentDesigned.h" // Assuming this includes Solution, Instance, Tour structs
#include <vector>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <cmath>     // For std::pow
#include "Utils.h"   // Provides getRandomNumber, getRandomFractionFast

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(20, 35); 

    std::unordered_set<int> selectedCustomers;
    
    if (numCustomersToRemove >= sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int firstCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(firstCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> currentSelectedVec(selectedCustomers.begin(), selectedCustomers.end());
        int c_ref_idx = getRandomNumber(0, static_cast<int>(currentSelectedVec.size()) - 1);
        int c_ref = currentSelectedVec[c_ref_idx];

        std::vector<std::pair<float, int>> candidate_scores;
        candidate_scores.reserve(sol.instance.numCustomers); 

        for (int c_i = 1; c_i <= sol.instance.numCustomers; ++c_i) {
            if (selectedCustomers.count(c_i)) { 
                continue;
            }

            float score = sol.instance.distanceMatrix[c_ref][c_i];
            
            if (sol.customerToTourMap[c_ref] == sol.customerToTourMap[c_i]) {
                score *= 0.5f; 
            }
            
            candidate_scores.push_back({score, c_i});
        }

        if (candidate_scores.empty()) { 
            break;
        }

        std::sort(candidate_scores.begin(), candidate_scores.end());

        int pool_size = std::min(static_cast<int>(candidate_scores.size()), 20); 
        float r = getRandomFractionFast(); 
        
        int idx_in_pool = static_cast<int>(std::pow(r, 2.0f) * pool_size); 
        idx_in_pool = std::min(idx_in_pool, pool_size - 1); 

        selectedCustomers.insert(candidate_scores[idx_in_pool].second);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    const float STOCHASTIC_FACTOR = 20.0f; 

    std::vector<std::pair<float, int>> customer_keys;
    customer_keys.reserve(customers.size());

    for (int customer_id : customers) {
        float key = instance.nodePositions[customer_id][0];
        key += (getRandomFractionFast() - 0.5f) * STOCHASTIC_FACTOR; 
        customer_keys.push_back({key, customer_id});
    }

    std::sort(customer_keys.begin(), customer_keys.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first < b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_keys[i].second;
    }
}