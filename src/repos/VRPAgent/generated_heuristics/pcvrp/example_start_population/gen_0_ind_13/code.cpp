#include "AgentDesigned.h"
#include <random> 
#include <unordered_set> 
#include <vector>        
#include <algorithm>     
#include <utility>       

// Customer selection for removal
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(8, 25); 

    if (numCustomersToRemove == 0) {
        return {};
    }

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer);

    std::vector<std::pair<float, int>> candidates;
    std::unordered_set<int> unique_candidate_ids;

    const int NEIGHBORS_TO_CONSIDER_PER_SELECTED = 10; 

    while (selectedCustomers.size() < numCustomersToRemove) {
        candidates.clear();
        unique_candidate_ids.clear();

        for (int s_cust : selectedCustomers) {
            int count_neighbors_considered = 0;
            for (int n_cust : sol.instance.adj[s_cust]) {
                if (selectedCustomers.count(n_cust) == 0 && unique_candidate_ids.count(n_cust) == 0) {
                    candidates.push_back({sol.instance.distanceMatrix[s_cust][n_cust], n_cust});
                    unique_candidate_ids.insert(n_cust);
                }
                count_neighbors_considered++;
                if (count_neighbors_considered >= NEIGHBORS_TO_CONSIDER_PER_SELECTED) {
                    break; 
                }
            }
        }
        
        int num_random_candidates_to_add = getRandomNumber(1, 3); 
        for (int i = 0; i < num_random_candidates_to_add; ++i) {
            int random_cust = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomers.count(random_cust) == 0 && unique_candidate_ids.count(random_cust) == 0) {
                candidates.push_back({1000000.0f, random_cust}); 
                unique_candidate_ids.insert(random_cust);
            }
        }

        if (candidates.empty()) {
            int next_customer = -1;
            int attempts = 0;
            const int MAX_ATTEMPTS = sol.instance.numCustomers * 2; 
            while (next_customer == -1 || selectedCustomers.count(next_customer) > 0) {
                if (selectedCustomers.size() == sol.instance.numCustomers || attempts > MAX_ATTEMPTS) {
                    next_customer = -1; 
                    break;
                }
                next_customer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (next_customer != -1) {
                selectedCustomers.insert(next_customer);
            } else {
                break; 
            }
        } else {
            std::sort(candidates.begin(), candidates.end());

            int top_k_range = std::min((int)candidates.size(), getRandomNumber(3, 10)); 
            int chosen_idx = getRandomNumber(0, top_k_range - 1);
            
            selectedCustomers.insert(candidates[chosen_idx].second);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function for ordering the removed customers for reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float base_score = 0.0f;

        base_score += instance.prizes[customer_id] / (instance.demand[customer_id] + 1e-6); 

        base_score += instance.prizes[customer_id] * 0.05f; 

        base_score -= instance.distanceMatrix[0][customer_id] * 0.001f;

        float final_score = base_score + (getRandomFractionFast() - 0.5f) * (base_score * 0.2f + 0.1f); 

        scored_customers.push_back({final_score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}