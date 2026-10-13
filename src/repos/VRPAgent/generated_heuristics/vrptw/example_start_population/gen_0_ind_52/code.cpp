#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> 
#include <vector>    
#include <cmath>     

float calculate_relatedness_dist(int c1_idx, int c2_idx, const Instance& instance) {
    return instance.distanceMatrix[c1_idx][c2_idx];
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> allCustomers;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        allCustomers.push_back(i);
    }

    int numCustomersToRemove = getRandomNumber(10, 25); 

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_customer_idx);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        std::vector<int> currentSelectedVec(selectedCustomersSet.begin(), selectedCustomersSet.end());
        int customer_ref_idx = currentSelectedVec[getRandomNumber(0, currentSelectedVec.size() - 1)];

        std::vector<std::pair<float, int>> candidates_relatedness;
        for (int customer_id : allCustomers) {
            if (selectedCustomersSet.find(customer_id) == selectedCustomersSet.end()) {
                float relatedness = calculate_relatedness_dist(customer_ref_idx, customer_id, sol.instance);
                candidates_relatedness.push_back({relatedness, customer_id});
            }
        }

        if (candidates_relatedness.empty()) {
            break; 
        }

        std::sort(candidates_relatedness.begin(), candidates_relatedness.end());

        float selection_bias_power = 3.0; 
        int num_candidates_available = candidates_relatedness.size();
        
        int chosen_idx_in_candidates_list = static_cast<int>(num_candidates_available * std::pow(getRandomFractionFast(), selection_bias_power));
        chosen_idx_in_candidates_list = std::min(chosen_idx_in_candidates_list, num_candidates_available - 1);

        selectedCustomersSet.insert(candidates_relatedness[chosen_idx_in_candidates_list].second);
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.TW_Width[customer_id] + instance.startTW[customer_id] * 0.1f; 
        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end());

    std::vector<int> sorted_customers_stochastic;
    sorted_customers_stochastic.reserve(customers.size());

    float selection_bias_power = 2.0; 
    
    while (!customer_scores.empty()) {
        int num_candidates_available = customer_scores.size();
        int chosen_idx_in_candidates_list = static_cast<int>(num_candidates_available * std::pow(getRandomFractionFast(), selection_bias_power));
        chosen_idx_in_candidates_list = std::min(chosen_idx_in_candidates_list, num_candidates_available - 1);

        sorted_customers_stochastic.push_back(customer_scores[chosen_idx_in_candidates_list].second);
        
        customer_scores.erase(customer_scores.begin() + chosen_idx_in_candidates_list);
    }
    
    customers = sorted_customers_stochastic;
}