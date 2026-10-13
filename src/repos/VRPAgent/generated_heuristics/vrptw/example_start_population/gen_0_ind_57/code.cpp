#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;
    std::vector<int> expansion_pool;

    int num_to_remove = getRandomNumber(10, 20);

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_seed);
    selected_customers_vec.push_back(initial_seed);
    expansion_pool.push_back(initial_seed);

    while (selected_customers_vec.size() < num_to_remove) {
        if (expansion_pool.empty()) {
            int new_seed = -1;
            int safety_counter = 0;
            while (new_seed == -1 || selected_customers_set.count(new_seed)) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter++;
                if (safety_counter > sol.instance.numCustomers * 2) {
                    return selected_customers_vec;
                }
            }
            selected_customers_set.insert(new_seed);
            selected_customers_vec.push_back(new_seed);
            expansion_pool.push_back(new_seed);
        }

        int pool_idx = getRandomNumber(0, expansion_pool.size() - 1);
        int current_customer = expansion_pool[pool_idx];

        std::swap(expansion_pool[pool_idx], expansion_pool.back());
        expansion_pool.pop_back();

        for (int neighbor_id : sol.instance.adj[current_customer]) {
            if (selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                selected_customers_set.insert(neighbor_id);
                selected_customers_vec.push_back(neighbor_id);
                expansion_pool.push_back(neighbor_id);

                if (selected_customers_vec.size() == num_to_remove) {
                    break;
                }
            }
        }
    }
    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    const float EPSILON = 0.001f;
    const float JITTER_MAGNITUDE = 0.01f;

    for (int customer_id : customers) {
        float base_score = 1.0f / (instance.TW_Width[customer_id] + EPSILON);
        float noisy_score = base_score + getRandomFraction(-JITTER_MAGNITUDE, JITTER_MAGNITUDE);
        scored_customers.emplace_back(noisy_score, customer_id);
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}