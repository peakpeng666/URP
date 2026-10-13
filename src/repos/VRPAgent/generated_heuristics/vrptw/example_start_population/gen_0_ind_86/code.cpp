#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> 
#include <vector>
#include <numeric>   
#include "Utils.h"   

std::vector<int> select_by_llm_1(const Solution& sol) {
    if (sol.instance.numCustomers == 0) {
        return {};
    }

    std::unordered_set<int> selectedCustomersSet;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        return {};
    }

    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_customer);

    std::vector<int> unselectedCustomersVec;
    unselectedCustomersVec.reserve(sol.instance.numCustomers);
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (i != initial_customer) {
            unselectedCustomersVec.push_back(i);
        }
    }
    
    std::unordered_set<int> candidatePoolSet; 
    const int max_neighbors_per_selected_customer = 10; 

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        candidatePoolSet.clear();

        for (int sel_cust : selectedCustomersSet) {
            int neighbors_added_from_this_sel_cust = 0;
            for (int neighbor_node_id : sol.instance.adj[sel_cust]) {
                if (neighbor_node_id == 0) continue; 
                if (selectedCustomersSet.find(neighbor_node_id) == selectedCustomersSet.end()) { 
                    candidatePoolSet.insert(neighbor_node_id);
                    neighbors_added_from_this_sel_cust++;
                    if (neighbors_added_from_this_sel_cust >= max_neighbors_per_selected_customer) {
                        break; 
                    }
                }
            }
        }

        int customer_to_add = -1;

        if (!candidatePoolSet.empty()) {
            std::vector<int> currentCandidates(candidatePoolSet.begin(), candidatePoolSet.end());
            int idx = getRandomNumber(0, static_cast<int>(currentCandidates.size()) - 1);
            customer_to_add = currentCandidates[idx];
        } else {
            if (!unselectedCustomersVec.empty()) {
                int idx = getRandomNumber(0, static_cast<int>(unselectedCustomersVec.size()) - 1);
                customer_to_add = unselectedCustomersVec[idx];
            } else {
                break;
            }
        }

        if (customer_to_add != -1) {
            selectedCustomersSet.insert(customer_to_add);
            for(size_t i = 0; i < unselectedCustomersVec.size(); ++i) {
                if (unselectedCustomersVec[i] == customer_to_add) {
                    unselectedCustomersVec[i] = unselectedCustomersVec.back();
                    unselectedCustomersVec.pop_back();
                    break;
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float WEIGHT_TIME_WINDOW_TIGHTNESS = 10.0f;
    const float WEIGHT_DEMAND = 1.0f;
    const float WEIGHT_SERVICE_TIME = 2.0f;
    const float NOISE_MAGNITUDE = 0.001f;

    std::vector<std::pair<float, int>> customer_scores; 
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float tw_tightness_component = 0.0f;
        if (instance.TW_Width[customer_id] > 0.001f) {
            tw_tightness_component = WEIGHT_TIME_WINDOW_TIGHTNESS / instance.TW_Width[customer_id];
        } else {
            tw_tightness_component = WEIGHT_TIME_WINDOW_TIGHTNESS * 1000.0f; 
        }
        
        float demand_component = WEIGHT_DEMAND * instance.demand[customer_id];
        float service_time_component = WEIGHT_SERVICE_TIME * instance.serviceTime[customer_id];
        
        float score = tw_tightness_component + demand_component + service_time_component;
        
        score += getRandomFractionFast() * NOISE_MAGNITUDE;
        
        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first; 
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}