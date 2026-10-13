#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> candidates_queue;

    int num_to_remove = getRandomNumber(15, 30);
    if (sol.instance.numCustomers < num_to_remove) {
        num_to_remove = sol.instance.numCustomers;
    }

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_seed);
    candidates_queue.push_back(initial_seed);

    while (selected_customers_set.size() < num_to_remove) {
        if (candidates_queue.empty()) {
            if (selected_customers_set.size() >= sol.instance.numCustomers) {
                break;
            }
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            while (selected_customers_set.count(new_seed) > 0) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selected_customers_set.insert(new_seed);
            candidates_queue.push_back(new_seed);
            if (selected_customers_set.size() == num_to_remove) break;
        }

        int q_idx = getRandomNumber(0, static_cast<int>(candidates_queue.size()) - 1);
        int current_customer_id = candidates_queue[q_idx];

        std::swap(candidates_queue[q_idx], candidates_queue.back());
        candidates_queue.pop_back();

        int num_neighbors_to_consider = std::min(static_cast<int>(sol.instance.adj[current_customer_id].size()), 5);
        for (int i = 0; i < num_neighbors_to_consider; ++i) {
            int neighbor_id = sol.instance.adj[current_customer_id][i];
            if (neighbor_id != 0 && selected_customers_set.count(neighbor_id) == 0) {
                selected_customers_set.insert(neighbor_id);
                candidates_queue.push_back(neighbor_id);
                if (selected_customers_set.size() == num_to_remove) {
                    break;
                }
            }
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float demand_component = static_cast<float>(instance.demand[customer_id]);
        float distance_component = instance.distanceMatrix[0][customer_id];
        
        float score = 
            demand_component * 2.0f +
            distance_component + 
            getRandomFractionFast() * 10.0f;

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}