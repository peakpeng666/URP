#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

void add_to_candidate_pool(int customer_id, std::vector<int>& candidate_pool_vec,
                           std::unordered_set<int>& in_candidate_pool_set,
                           const std::unordered_set<int>& selected_customers,
                           const Instance& instance, int num_neighbors_to_add) {
    if (customer_id == 0) { // Skip depot if it somehow gets passed
        return;
    }
    if (selected_customers.find(customer_id) == selected_customers.end() &&
        in_candidate_pool_set.find(customer_id) == in_candidate_pool_set.end()) {
        candidate_pool_vec.push_back(customer_id);
        in_candidate_pool_set.insert(customer_id);
    }

    const auto& adj_list = instance.adj[customer_id];
    for (size_t i = 0; i < std::min((size_t)num_neighbors_to_add, adj_list.size()); ++i) {
        int neighbor_id = adj_list[i];
        if (neighbor_id != 0 &&
            selected_customers.find(neighbor_id) == selected_customers.end() &&
            in_candidate_pool_set.find(neighbor_id) == in_candidate_pool_set.end()) {
            candidate_pool_vec.push_back(neighbor_id);
            in_candidate_pool_set.insert(neighbor_id);
        }
    }
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    int min_customers_to_remove = 10;
    int max_customers_to_remove = 25;
    int num_neighbors_to_expand = 8;
    float random_seed_prob = 0.2f;

    std::unordered_set<int> selected_customers;
    std::vector<int> candidate_pool_vec;
    std::unordered_set<int> in_candidate_pool_set;

    int num_customers_target = getRandomNumber(min_customers_to_remove, max_customers_to_remove);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers.insert(initial_customer);
    add_to_candidate_pool(initial_customer, candidate_pool_vec, in_candidate_pool_set,
                          selected_customers, sol.instance, num_neighbors_to_expand);

    while (selected_customers.size() < num_customers_target) {
        bool picked_from_candidate_pool = false;

        if (!candidate_pool_vec.empty() && getRandomFractionFast() > random_seed_prob) {
            int rand_idx = getRandomNumber(0, candidate_pool_vec.size() - 1);
            int customer_to_add = candidate_pool_vec[rand_idx];

            candidate_pool_vec[rand_idx] = candidate_pool_vec.back();
            candidate_pool_vec.pop_back();
            in_candidate_pool_set.erase(customer_to_add);

            if (selected_customers.find(customer_to_add) == selected_customers.end()) {
                selected_customers.insert(customer_to_add);
                add_to_candidate_pool(customer_to_add, candidate_pool_vec, in_candidate_pool_set,
                                      selected_customers, sol.instance, num_neighbors_to_expand);
                picked_from_candidate_pool = true;
            }
        }

        if (!picked_from_candidate_pool) {
            int new_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
            int safety_counter = 0;
            while (selected_customers.find(new_seed_customer) != selected_customers.end() && safety_counter < sol.instance.numCustomers * 2) {
                new_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter++;
            }

            if (selected_customers.find(new_seed_customer) == selected_customers.end()) {
                selected_customers.insert(new_seed_customer);
                add_to_candidate_pool(new_seed_customer, candidate_pool_vec, in_candidate_pool_set,
                                      selected_customers, sol.instance, num_neighbors_to_expand);
            }
        }
    }

    return std::vector<int>(selected_customers.begin(), selected_customers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float w_tw = 0.4f;
    float w_dist = 0.3f;
    float w_st = 0.2f;
    float random_noise_factor = 0.1f;

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float tw_score = 0.0f;
        if (instance.TW_Width[customer_id] > 0.001f) {
            tw_score = 1.0f / instance.TW_Width[customer_id];
        } else {
            tw_score = 1000.0f;
        }

        float dist_score = instance.distanceMatrix[0][customer_id];
        float st_score = instance.serviceTime[customer_id];

        float combined_score = (w_tw * tw_score) + (w_dist * dist_score) + (w_st * st_score);
        float random_noise = random_noise_factor * getRandomFractionFast();
        float final_score = combined_score + random_noise;

        scored_customers.push_back({final_score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}