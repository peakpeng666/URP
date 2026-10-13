#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort, std::shuffle
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_to_remove = getRandomNumber(10, 20); 
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec; 

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(seed_customer);
    selected_customers_vec.push_back(seed_customer);

    while (selected_customers_vec.size() < num_to_remove) {
        bool added_new = false;
        
        int source_idx = getRandomNumber(0, selected_customers_vec.size() - 1);
        int source_customer = selected_customers_vec[source_idx];

        int neighbors_checked_count = 0;
        const int MAX_NEIGHBORS_TO_CHECK = 30; 

        for (int neighbor_node_id : sol.instance.adj[source_customer]) {
            if (neighbor_node_id == 0) continue; 
            if (neighbor_node_id > sol.instance.numCustomers) continue; 

            if (selected_customers_set.find(neighbor_node_id) == selected_customers_set.end()) {
                selected_customers_set.insert(neighbor_node_id);
                selected_customers_vec.push_back(neighbor_node_id);
                added_new = true;
                break; 
            }
            neighbors_checked_count++;
            if (neighbors_checked_count >= MAX_NEIGHBORS_TO_CHECK) break;
        }

        if (!added_new) {
            int random_customer;
            do {
                random_customer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selected_customers_set.find(random_customer) != selected_customers_set.end());
            selected_customers_set.insert(random_customer);
            selected_customers_vec.push_back(random_customer);
        }
    }

    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers; 
    std::unordered_set<int> removed_customers_set(customers.begin(), customers.end());

    const int MAX_NEIGHBORS_FOR_SCORE = 20; 
    for (int customer_id : customers) {
        float connectedness_score = 0.0f;
        int neighbors_checked = 0;
        for (int neighbor_node_id : instance.adj[customer_id]) {
            if (neighbor_node_id == 0) continue; 
            if (neighbor_node_id > instance.numCustomers) continue; 

            if (removed_customers_set.count(neighbor_node_id)) {
                connectedness_score += 1.0f;
            }
            neighbors_checked++;
            if (neighbors_checked >= MAX_NEIGHBORS_FOR_SCORE) {
                break; 
            }
        }
        
        connectedness_score += getRandomFractionFast() * 0.1f;

        scored_customers.push_back({connectedness_score, customer_id});
    }

    bool sort_descending = true; 
    if (getRandomFractionFast() < 0.2f) { 
        sort_descending = false;
    }

    if (sort_descending) {
        std::sort(scored_customers.begin(), scored_customers.end(), 
            [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                if (a.first != b.first) {
                    return a.first > b.first; 
                }
                return a.second < b.second; 
            });
    } else {
        std::sort(scored_customers.begin(), scored_customers.end(), 
            [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                if (a.first != b.first) {
                    return a.first < b.first; 
                }
                return a.second < b.second; 
            });
    }
    
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}