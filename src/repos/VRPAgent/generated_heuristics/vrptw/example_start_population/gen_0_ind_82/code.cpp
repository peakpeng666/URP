#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <numeric>

#include "Utils.h"
#include "Instance.h"
#include "Solution.h"
#include "Tour.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;
    std::vector<bool> is_customer_selected(sol.instance.numCustomers + 1, false);

    int num_customers_to_remove = 15 + getRandomNumber(0, 10);

    std::vector<int> all_customer_ids(sol.instance.numCustomers);
    std::iota(all_customer_ids.begin(), all_customer_ids.end(), 1);
    static thread_local std::mt19937 gen(std::random_device{}());
    std::shuffle(all_customer_ids.begin(), all_customer_ids.end(), gen);
    int current_random_idx = 0;

    if (sol.instance.numCustomers == 0) {
        return {};
    }
    
    int initial_customer_id = all_customer_ids[current_random_idx++];
    selected_customers_set.insert(initial_customer_id);
    selected_customers_vec.push_back(initial_customer_id);
    is_customer_selected[initial_customer_id] = true;

    while (selected_customers_set.size() < num_customers_to_remove && current_random_idx < sol.instance.numCustomers) {
        int customer_to_add = -1;

        if (getRandomFraction() < 0.2f) {
            while (current_random_idx < sol.instance.numCustomers && is_customer_selected[all_customer_ids[current_random_idx]]) {
                current_random_idx++;
            }
            if (current_random_idx < sol.instance.numCustomers) {
                customer_to_add = all_customer_ids[current_random_idx++];
            }
        } else {
            int anchor_customer_idx_in_vec = getRandomNumber(0, selected_customers_vec.size() - 1);
            int anchor_customer_id = selected_customers_vec[anchor_customer_idx_in_vec];

            for (int neighbor_id : sol.instance.adj[anchor_customer_id]) {
                if (neighbor_id == 0) continue; 
                if (neighbor_id > sol.instance.numCustomers) continue; // Ensure neighbor_id is within valid customer range
                if (!is_customer_selected[neighbor_id]) {
                    customer_to_add = neighbor_id;
                    break;
                }
            }

            if (customer_to_add == -1) {
                while (current_random_idx < sol.instance.numCustomers && is_customer_selected[all_customer_ids[current_random_idx]]) {
                    current_random_idx++;
                }
                if (current_random_idx < sol.instance.numCustomers) {
                    customer_to_add = all_customer_ids[current_random_idx++];
                }
            }
        }

        if (customer_to_add != -1) {
            selected_customers_set.insert(customer_to_add);
            selected_customers_vec.push_back(customer_to_add);
            is_customer_selected[customer_to_add] = true;
        } else {
            break;
        }
    }

    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::sort(customers.begin(), customers.end(), [&](int c1_id, int c2_id) {
        float tw_width1 = instance.TW_Width[c1_id];
        float tw_width2 = instance.TW_Width[c2_id];

        float demand_factor1 = (1.0f - static_cast<float>(instance.demand[c1_id]) / instance.vehicleCapacity) * 0.001f;
        float demand_factor2 = (1.0f - static_cast<float>(instance.demand[c2_id]) / instance.vehicleCapacity) * 0.001f;

        float service_time_factor1 = (1.0f - instance.serviceTime[c1_id] / 100.0f) * 0.0001f; 
        float service_time_factor2 = (1.0f - instance.serviceTime[c2_id] / 100.0f) * 0.0001f;

        float random_perturbation1 = getRandomFractionFast() * 0.00001f;
        float random_perturbation2 = getRandomFractionFast() * 0.00001f;

        float score1 = tw_width1 + demand_factor1 + service_time_factor1 + random_perturbation1;
        float score2 = tw_width2 + demand_factor2 + service_time_factor2 + random_perturbation2;

        return score1 < score2;
    });
}