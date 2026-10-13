#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"
#include "AgentDesigned.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_list;
    std::vector<int> frontier_customers;

    int min_to_remove = 10;
    int max_to_remove = 25;
    int num_to_remove = getRandomNumber(min_to_remove, max_to_remove);

    if (num_to_remove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    
    selected_customers_set.insert(initial_seed_customer_id);
    selected_customers_list.push_back(initial_seed_customer_id);
    frontier_customers.push_back(initial_seed_customer_id);

    while (selected_customers_list.size() < num_to_remove) {
        if (frontier_customers.empty()) {
            int new_seed_found = -1;
            int attempts = 0;
            const int max_attempts = sol.instance.numCustomers * 2; 

            while (new_seed_found == -1 && attempts < max_attempts) { 
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(potential_seed) == selected_customers_set.end()) {
                    new_seed_found = potential_seed;
                }
                attempts++;
            }

            if (new_seed_found != -1) {
                selected_customers_set.insert(new_seed_found);
                selected_customers_list.push_back(new_seed_found);
                frontier_customers.push_back(new_seed_found);
            } else {
                break; 
            }
        }
        
        int frontier_idx = getRandomNumber(0, frontier_customers.size() - 1);
        int current_customer_id = frontier_customers[frontier_idx];
        std::swap(frontier_customers[frontier_idx], frontier_customers.back());
        frontier_customers.pop_back();

        for (int neighbor_node_id : sol.instance.adj[current_customer_id]) {
            if (neighbor_node_id == 0) {
                continue;
            }
            if (neighbor_node_id <= sol.instance.numCustomers && 
                selected_customers_set.find(neighbor_node_id) == selected_customers_set.end()) 
            {
                selected_customers_set.insert(neighbor_node_id);
                selected_customers_list.push_back(neighbor_node_id);
                frontier_customers.push_back(neighbor_node_id);

                if (selected_customers_list.size() == num_to_remove) {
                    return selected_customers_list;
                }
            }
        }
    }

    return selected_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    struct CustomerSortInfo {
        int customer_id;
        float sort_key;
    };

    std::vector<CustomerSortInfo> sort_data;
    sort_data.reserve(customers.size());

    for (int customer_id : customers) {
        float dist_to_depot = instance.distanceMatrix[0][customer_id];
        float perturbed_dist = dist_to_depot + getRandomFractionFast() * 0.01f; 

        sort_data.push_back({customer_id, perturbed_dist});
    }

    std::sort(sort_data.begin(), sort_data.end(), [](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        return a.sort_key > b.sort_key;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data[i].customer_id;
    }
}