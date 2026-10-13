#include "AgentDesigned.h"
#include "Utils.h"
#include <vector>
#include <algorithm>
#include <random>
#include <unordered_set>
#include <cmath>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_list;

    int num_customers_to_remove = getRandomNumber(15, 30);

    if (num_customers_to_remove > sol.instance.numCustomers) {
        num_customers_to_remove = sol.instance.numCustomers;
    }
    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (num_customers_to_remove == 0) {
        num_customers_to_remove = 1; 
    }

    int seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(seed_customer_id);
    selected_list.push_back(seed_customer_id);

    while (selected_set.size() < num_customers_to_remove) {
        int reference_customer_idx = getRandomNumber(0, static_cast<int>(selected_list.size()) - 1);
        int reference_customer_id = selected_list[reference_customer_idx];

        int neighbor_to_add = -1;
        int checked_neighbors_count = 0;
        
        for (int current_neighbor_id : sol.instance.adj[reference_customer_id]) {
            if (current_neighbor_id <= 0 || current_neighbor_id > sol.instance.numCustomers) {
                continue;
            }
            if (selected_set.count(current_neighbor_id)) {
                continue;
            }

            if (getRandomFraction() < 0.7) {
                neighbor_to_add = current_neighbor_id;
                break;
            }

            checked_neighbors_count++;
            if (checked_neighbors_count > 15) {
                break;
            }
        }

        if (neighbor_to_add != -1) {
            selected_set.insert(neighbor_to_add);
            selected_list.push_back(neighbor_to_add);
        } else {
            int random_customer_fallback;
            do {
                random_customer_fallback = getRandomNumber(1, sol.instance.numCustomers);
            } while (selected_set.count(random_customer_fallback));
            
            selected_set.insert(random_customer_fallback);
            selected_list.push_back(random_customer_fallback);
        }
    }

    return selected_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    std::vector<std::pair<float, int>> sort_data;
    sort_data.reserve(customers.size());
    for (int customer_id : customers) {
        sort_data.push_back({instance.startTW[customer_id], customer_id});
    }

    std::sort(sort_data.begin(), sort_data.end());

    float swap_probability = 0.15f;
    int swap_range = 3;

    for (size_t i = 0; i < sort_data.size(); ++i) {
        if (getRandomFractionFast() < swap_probability) {
            int j_min = std::max(0, static_cast<int>(i) - swap_range);
            int j_max = std::min(static_cast<int>(sort_data.size()) - 1, static_cast<int>(i) + swap_range);
            
            if (j_min <= j_max) {
                int j = getRandomNumber(j_min, j_max);
                std::swap(sort_data[i], sort_data[j]);
            }
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data[i].second;
    }
}