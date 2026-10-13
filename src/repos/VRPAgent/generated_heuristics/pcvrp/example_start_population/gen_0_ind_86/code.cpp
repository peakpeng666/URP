#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>


// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatePoolVec; 
    std::unordered_set<int> candidatePoolSet; 

    int min_remove = 10;
    int max_remove = 25; 
    int numCustomersToRemove = getRandomNumber(min_remove, max_remove);

    if (numCustomersToRemove <= 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    int seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer_id);

    int num_initial_neighbors_to_explore = std::min((int)sol.instance.adj[seed_customer_id].size(), 5); 
    for (int i = 0; i < num_initial_neighbors_to_explore; ++i) {
        int neighbor = sol.instance.adj[seed_customer_id][i];
        if (selectedCustomers.find(neighbor) == selectedCustomers.end() && candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
            candidatePoolVec.push_back(neighbor);
            candidatePoolSet.insert(neighbor);
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidatePoolVec.empty()) {
            int new_seed_id = -1;
            int attempts = 0;
            while (attempts < sol.instance.numCustomers * 2 && selectedCustomers.size() < sol.instance.numCustomers) {
                new_seed_id = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(new_seed_id) == selectedCustomers.end()) {
                    break;
                }
                attempts++;
            }
            
            if (new_seed_id != -1 && selectedCustomers.find(new_seed_id) == selectedCustomers.end()) {
                selectedCustomers.insert(new_seed_id);
                int num_neighbors_to_explore = std::min((int)sol.instance.adj[new_seed_id].size(), 5);
                for (int i = 0; i < num_neighbors_to_explore; ++i) {
                    int neighbor = sol.instance.adj[new_seed_id][i];
                    if (selectedCustomers.find(neighbor) == selectedCustomers.end() && candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
                        candidatePoolVec.push_back(neighbor);
                        candidatePoolSet.insert(neighbor);
                    }
                }
            } else {
                break; 
            }
        } else {
            int pool_idx = getRandomNumber(0, candidatePoolVec.size() - 1);
            int customer_to_add = candidatePoolVec[pool_idx];

            candidatePoolVec[pool_idx] = candidatePoolVec.back();
            candidatePoolVec.pop_back();
            candidatePoolSet.erase(customer_to_add);

            selectedCustomers.insert(customer_to_add); 

            float p_add_neighbor_to_pool = 0.7f; 
            int num_neighbors_to_explore = std::min((int)sol.instance.adj[customer_to_add].size(), 5); 
            for (int i = 0; i < num_neighbors_to_explore; ++i) {
                int neighbor = sol.instance.adj[customer_to_add][i];
                if (getRandomFractionFast() < p_add_neighbor_to_pool) { 
                    if (selectedCustomers.find(neighbor) == selectedCustomers.end() && candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
                        candidatePoolVec.push_back(neighbor);
                        candidatePoolSet.insert(neighbor);
                    }
                }
            }
        }
    }
    
    while (selectedCustomers.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomers.insert(randomCustomer); 
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float alpha_prize_demand = 1.0f; 
    float beta_dist_depot = 0.5f; 
    float noise_magnitude = 0.1f; 

    std::vector<std::pair<float, int>> scored_customers; 
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float demand_val = static_cast<float>(instance.demand[customer_id]);
        float prize_val = instance.prizes[customer_id];
        float dist_depot_val = instance.distanceMatrix[0][customer_id];

        float prize_to_demand_ratio;
        if (demand_val > 0.0f) {
            prize_to_demand_ratio = prize_val / demand_val;
        } else {
            prize_to_demand_ratio = prize_val * 1000.0f; 
        }
        
        float inv_dist_depot;
        if (dist_depot_val > 0.0f) {
            inv_dist_depot = 1.0f / dist_depot_val;
        } else {
            inv_dist_depot = 1000.0f; 
        }

        float score = alpha_prize_demand * prize_to_demand_ratio + beta_dist_depot * inv_dist_depot;

        score += getRandomFraction(-noise_magnitude, noise_magnitude); 

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}