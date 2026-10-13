#include <vector>
#include <unordered_set>
#include <random>
#include <algorithm> // For std::min, std::max, std::sort
#include <utility>   // For std::pair

// Include necessary headers for Solution, Instance, and Utils
// Assuming AgentDesigned.h will include these, but explicit includes are safer.
#include "Solution.h"
#include "Instance.h"
#include "Utils.h"

// Static random number generator for performance in select_by_llm_1
static thread_local std::mt19937 select_gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    int min_remove_count = 15;
    int max_remove_count = 30;
    int neighbor_consideration_count = 10;

    int num_to_remove = getRandomNumber(min_remove_count, max_remove_count);
    num_to_remove = std::min(num_to_remove, sol.instance.numCustomers);

    std::unordered_set<int> selected_customers_set;
    std::vector<bool> is_customer_selected(sol.instance.numCustomers + 1, false);

    if (sol.instance.numCustomers == 0 || num_to_remove == 0) {
        return {};
    }

    int seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(seed_customer_id);
    is_customer_selected[seed_customer_id] = true;

    while (selected_customers_set.size() < num_to_remove) {
        std::vector<int> candidate_pool;
        std::unordered_set<int> candidate_pool_set;

        for (int selected_cust_id : selected_customers_set) {
            const auto& adj_list = sol.instance.adj[selected_cust_id];
            for (size_t i = 0; i < std::min((size_t)neighbor_consideration_count, adj_list.size()); ++i) {
                int neighbor_cust_id = adj_list[i];
                
                if (neighbor_cust_id >= 1 && neighbor_cust_id <= sol.instance.numCustomers && !is_customer_selected[neighbor_cust_id]) {
                    if (candidate_pool_set.find(neighbor_cust_id) == candidate_pool_set.end()) {
                        candidate_pool.push_back(neighbor_cust_id);
                        candidate_pool_set.insert(neighbor_cust_id);
                    }
                }
            }
        }

        if (candidate_pool.empty()) {
            std::vector<int> remaining_unselected;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (!is_customer_selected[i]) {
                    remaining_unselected.push_back(i);
                }
            }
            if (remaining_unselected.empty()) {
                break;
            }
            std::uniform_int_distribution<> distrib(0, remaining_unselected.size() - 1);
            int next_customer_id = remaining_unselected[distrib(select_gen)];
            selected_customers_set.insert(next_customer_id);
            is_customer_selected[next_customer_id] = true;
        } else {
            std::uniform_int_distribution<> distrib(0, candidate_pool.size() - 1);
            int next_customer_id = candidate_pool[distrib(select_gen)];
            selected_customers_set.insert(next_customer_id);
            is_customer_selected[next_customer_id] = true;
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float max_tw_width = 0.0;
    float max_distance_from_depot = 0.0;
    int max_demand = 0;

    for (int customer_id : customers) {
        max_tw_width = std::max(max_tw_width, instance.TW_Width[customer_id]);
        max_distance_from_depot = std::max(max_distance_from_depot, instance.distanceMatrix[0][customer_id]);
        max_demand = std::max(max_demand, instance.demand[customer_id]);
    }

    float weight_tw = 0.4;
    float weight_dist = 0.3;
    float weight_demand = 0.2;
    float weight_stochastic = 0.1;

    std::vector<std::pair<float, int>> customer_priorities;
    customer_priorities.reserve(customers.size());

    for (int customer_id : customers) {
        float priority = 0.0;

        float norm_tw_width = (max_tw_width > 0.0) ? (instance.TW_Width[customer_id] / max_tw_width) : 0.0;
        priority += weight_tw * (1.0 - norm_tw_width);

        float norm_distance = (max_distance_from_depot > 0.0) ? (instance.distanceMatrix[0][customer_id] / max_distance_from_depot) : 0.0;
        priority += weight_dist * norm_distance;

        float norm_demand = (max_demand > 0) ? (static_cast<float>(instance.demand[customer_id]) / max_demand) : 0.0;
        priority += weight_demand * norm_demand;

        priority += getRandomFractionFast() * weight_stochastic;

        customer_priorities.push_back({priority, customer_id});
    }

    std::sort(customer_priorities.begin(), customer_priorities.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_priorities[i].second;
    }
}