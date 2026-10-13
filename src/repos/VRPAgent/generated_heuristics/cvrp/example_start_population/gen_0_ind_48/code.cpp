#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>
#include "Utils.h"

constexpr int LLM1_NUM_CUSTOMERS_TO_REMOVE_MIN = 15;
constexpr int LLM1_NUM_CUSTOMERS_TO_REMOVE_MAX = 30;
constexpr int LLM1_REMOVAL_NEIGHBORS_CONSIDERED = 20;
constexpr int LLM1_REMOVAL_TOP_POOL_SIZE = 5;       

constexpr float LLM1_SORT_NOISE_FACTOR = 0.05f; 
constexpr int LLM1_SORT_NEIGHBORS_CONSIDERED = 10; 

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_vec;

    int num_customers_to_remove = getRandomNumber(LLM1_NUM_CUSTOMERS_TO_REMOVE_MIN, LLM1_NUM_CUSTOMERS_TO_REMOVE_MAX);

    int seed_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(seed_customer_idx);
    selected_vec.push_back(seed_customer_idx);

    while (selected_vec.size() < num_customers_to_remove) {
        int c_ref_idx = getRandomNumber(0, selected_vec.size() - 1);
        int c_ref = selected_vec[c_ref_idx];

        std::vector<std::pair<float, int>> candidates;

        for (int i = 0; i < std::min((int)sol.instance.adj[c_ref].size(), LLM1_REMOVAL_NEIGHBORS_CONSIDERED); ++i) {
            int c_neighbor = sol.instance.adj[c_ref][i];
            if (c_neighbor >= 1 && c_neighbor <= sol.instance.numCustomers && selected_set.find(c_neighbor) == selected_set.end()) {
                float dist = sol.instance.distanceMatrix[c_ref][c_neighbor];
                float score = 1.0f / (dist + 1e-6f);
                candidates.push_back({score, c_neighbor});
            }
        }

        if (candidates.empty()) {
            int new_random_customer;
            do {
                new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selected_set.find(new_random_customer) != selected_set.end());
            selected_set.insert(new_random_customer);
            selected_vec.push_back(new_random_customer);
        } else {
            std::sort(candidates.begin(), candidates.end(), [](const auto& a, const auto& b) {
                return a.first > b.first;
            });

            int pool_size = std::min((int)candidates.size(), LLM1_REMOVAL_TOP_POOL_SIZE);
            int rand_idx_in_pool = getRandomNumber(0, pool_size - 1);
            int chosen_customer = candidates[rand_idx_in_pool].second;

            selected_set.insert(chosen_customer);
            selected_vec.push_back(chosen_customer);
        }
    }

    return selected_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    std::unordered_set<int> removed_customer_set(customers.begin(), customers.end());

    for (int customer_id : customers) {
        float priority_score = 0.0f;

        priority_score += static_cast<float>(instance.demand[customer_id]);

        priority_score += 1.0f / (instance.distanceMatrix[0][customer_id] + 1e-6f);

        float sum_inv_dist_to_removed_neighbors = 0.0f;
        int num_removed_neighbors = 0;

        for (int i = 0; i < std::min((int)instance.adj[customer_id].size(), LLM1_SORT_NEIGHBORS_CONSIDERED); ++i) {
            int neighbor_id = instance.adj[customer_id][i];
            if (neighbor_id >= 1 && neighbor_id <= instance.numCustomers && removed_customer_set.count(neighbor_id)) {
                float dist = instance.distanceMatrix[customer_id][neighbor_id];
                sum_inv_dist_to_removed_neighbors += 1.0f / (dist + 1e-6f);
                num_removed_neighbors++;
            }
        }
        if (num_removed_neighbors > 0) {
            priority_score += sum_inv_dist_to_removed_neighbors / num_removed_neighbors;
        }

        priority_score += getRandomFractionFast() * LLM1_SORT_NOISE_FACTOR;

        customer_scores.push_back({priority_score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}