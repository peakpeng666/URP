#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <numeric>
#include <unordered_set>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomers = sol.instance.numCustomers;
    int numNodes = sol.instance.numNodes;

    int num_to_remove = getRandomNumber(20, std::min(numCustomers, 50)); 

    std::vector<int> selected_customers_list;
    selected_customers_list.reserve(num_to_remove);

    std::vector<bool> is_selected(numNodes + 1, false); 

    int attempts_to_find_new_seed = 0;
    const int MAX_SEED_ATTEMPTS = 50; 

    while (selected_customers_list.size() < num_to_remove) {
        int customer_to_expand_from = -1;
        bool expanded_this_step = false;

        if (!selected_customers_list.empty()) {
            int rand_selected_idx = getRandomNumber(0, selected_customers_list.size() - 1);
            customer_to_expand_from = selected_customers_list[rand_selected_idx];

            const auto& neighbors = sol.instance.adj[customer_to_expand_from];
            
            std::vector<int> potential_new_customers;
            int adj_consider_limit = std::min((int)neighbors.size(), 15); // Consider up to 15 closest neighbors
            for(int i = 0; i < adj_consider_limit; ++i) {
                int neighbor_id = neighbors[i];
                if (neighbor_id != 0 && !is_selected[neighbor_id]) {
                    potential_new_customers.push_back(neighbor_id);
                }
            }

            if (!potential_new_customers.empty()) {
                int chosen_idx = getRandomNumber(0, potential_new_customers.size() - 1);
                int customer_to_add = potential_new_customers[chosen_idx];

                selected_customers_list.push_back(customer_to_add);
                is_selected[customer_to_add] = true;
                expanded_this_step = true;
                attempts_to_find_new_seed = 0; 
            }
        }

        if (!expanded_this_step) {
            attempts_to_find_new_seed++;
            if (attempts_to_find_new_seed >= MAX_SEED_ATTEMPTS) {
                int new_random_seed = -1;
                int safety_counter = 0;
                while(safety_counter < numCustomers * 2) { 
                    int candidate = getRandomNumber(1, numCustomers);
                    if (!is_selected[candidate]) {
                        new_random_seed = candidate;
                        break;
                    }
                    safety_counter++;
                }

                if (new_random_seed != -1) {
                    selected_customers_list.push_back(new_random_seed);
                    is_selected[new_random_seed] = true;
                    attempts_to_find_new_seed = 0; 
                } else {
                    break; 
                }
            }
        }
    }
    return selected_customers_list;
}

struct CustomerSortInfo {
    int id;
    float score;
};

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<CustomerSortInfo> sort_data;
    sort_data.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.TW_Width[customer_id]; 
        score += getRandomFractionFast() * 10.0f; 
        score += instance.distanceMatrix[0][customer_id] * 0.001f; 
        sort_data.push_back({customer_id, score});
    }

    std::sort(sort_data.begin(), sort_data.end(), [](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        return a.score < b.score;
    });

    for (size_t i = 0; i < sort_data.size(); ++i) {
        customers[i] = sort_data[i].id;
    }
}