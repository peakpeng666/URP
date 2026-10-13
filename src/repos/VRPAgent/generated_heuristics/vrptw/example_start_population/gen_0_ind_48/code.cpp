#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    int min_remove = 20;
    int max_remove = 40;
    int num_to_remove = getRandomNumber(min_remove, max_remove);

    std::unordered_set<int> selected_customers_set;
    std::vector<int> candidates_to_expand;

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(seed_customer);
    candidates_to_expand.push_back(seed_customer);

    int max_neighbor_options = 5;

    while (selected_customers_set.size() < num_to_remove) {
        if (candidates_to_expand.empty()) {
            int new_seed_customer;
            do {
                new_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selected_customers_set.count(new_seed_customer));

            selected_customers_set.insert(new_seed_customer);
            candidates_to_expand.push_back(new_seed_customer);

            if (selected_customers_set.size() == num_to_remove) break;
        }

        int rand_idx_in_candidates = getRandomNumber(0, static_cast<int>(candidates_to_expand.size() - 1));
        int current_node_for_expansion = candidates_to_expand[rand_idx_in_candidates];

        std::vector<int> available_neighbors;
        for (int neighbor_node : sol.instance.adj[current_node_for_expansion]) {
            if (selected_customers_set.find(neighbor_node) == selected_customers_set.end()) {
                available_neighbors.push_back(neighbor_node);
                if (available_neighbors.size() >= max_neighbor_options) break;
            }
        }

        if (!available_neighbors.empty()) {
            int chosen_neighbor = available_neighbors[getRandomNumber(0, static_cast<int>(available_neighbors.size() - 1))];
            selected_customers_set.insert(chosen_neighbor);
            candidates_to_expand.push_back(chosen_neighbor);
        } else {
            candidates_to_expand[rand_idx_in_candidates] = candidates_to_expand.back();
            candidates_to_expand.pop_back();
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen_sort(std::random_device{}());

    float rand_val = getRandomFraction(0.0, 1.0);
    if (rand_val < 0.85) {
        std::vector<std::pair<float, int>> customer_tw_data;
        customer_tw_data.reserve(customers.size());
        for (int customer_id : customers) {
            float perturbed_tw_width = instance.TW_Width[customer_id] + getRandomFractionFast() * 0.01;
            customer_tw_data.push_back({perturbed_tw_width, customer_id});
        }

        std::sort(customer_tw_data.begin(), customer_tw_data.end(),
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                      return a.first < b.first;
                  });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_tw_data[i].second;
        }
    } else {
        std::shuffle(customers.begin(), customers.end(), gen_sort);
    }
}