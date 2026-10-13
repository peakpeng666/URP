#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    std::unordered_set<int> selected_customers_set;
    std::vector<int> candidate_neighbors_vec;

    int min_removals = 10;
    int max_removals = 20;
    int num_to_remove = getRandomNumber(min_removals, max_removals);

    int seed_customer = getRandomNumber(1, instance.numCustomers);
    selected_customers_set.insert(seed_customer);

    if (seed_customer < instance.adj.size()) {
        for (int neighbor : instance.adj[seed_customer]) {
            if (neighbor >= 1 && neighbor <= instance.numCustomers && selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                candidate_neighbors_vec.push_back(neighbor);
            }
        }
    }

    while (selected_customers_set.size() < num_to_remove && !candidate_neighbors_vec.empty()) {
        int random_idx = getRandomNumber(0, candidate_neighbors_vec.size() - 1);
        int next_customer = candidate_neighbors_vec[random_idx];

        if (random_idx != candidate_neighbors_vec.size() - 1) {
            std::swap(candidate_neighbors_vec[random_idx], candidate_neighbors_vec.back());
        }
        candidate_neighbors_vec.pop_back();

        if (selected_customers_set.find(next_customer) == selected_customers_set.end()) {
            selected_customers_set.insert(next_customer);

            if (next_customer < instance.adj.size()) {
                for (int neighbor : instance.adj[next_customer]) {
                    if (neighbor >= 1 && neighbor <= instance.numCustomers && selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                        candidate_neighbors_vec.push_back(neighbor);
                    }
                }
            }
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<float> scores;
    scores.reserve(customers.size());

    for (int customer_id : customers) {
        if (customer_id >= 0 && customer_id < instance.numNodes) {
            float prize = instance.prizes[customer_id];
            float demand = static_cast<float>(instance.demand[customer_id]);
            float dist_from_depot = instance.distanceMatrix[0][customer_id];

            float effective_demand = std::max(1.0f, demand);
            float score = prize / effective_demand;
            score -= dist_from_depot * 0.1f;

            score += getRandomFractionFast() * 0.1f;

            scores.push_back(score);
        } else {
            scores.push_back(-1e9);
        }
    }

    std::vector<int> sorted_indices = argsort(scores);

    std::vector<int> sorted_customers;
    sorted_customers.reserve(customers.size());

    for (int i = sorted_indices.size() - 1; i >= 0; --i) {
        sorted_customers.push_back(customers[sorted_indices[i]]);
    }

    customers = sorted_customers;
}