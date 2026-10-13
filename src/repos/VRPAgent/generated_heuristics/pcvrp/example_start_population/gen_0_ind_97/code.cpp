#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_list;

    int min_to_remove = 15;
    int max_to_remove = 30;
    int num_to_remove = getRandomNumber(min_to_remove, max_to_remove);

    int num_initial_seeds = getRandomNumber(1, 3);
    float exploration_prob = 0.8f;
    int max_neighbors_to_check = 10;

    while (selected_customers_list.size() < num_initial_seeds && selected_customers_list.size() < num_to_remove) {
        int c_seed = getRandomNumber(1, sol.instance.numCustomers);
        if (selected_customers_set.find(c_seed) == selected_customers_set.end()) {
            selected_customers_set.insert(c_seed);
            selected_customers_list.push_back(c_seed);
        }
    }

    while (selected_customers_list.size() < num_to_remove) {
        int candidate_customer = -1;

        if (!selected_customers_list.empty() && getRandomFractionFast() < exploration_prob) {
            int source_customer_idx = getRandomNumber(0, selected_customers_list.size() - 1);
            int source_customer = selected_customers_list[source_customer_idx];

            const std::vector<int>& neighbors = sol.instance.adj[source_customer];
            std::vector<int> potential_neighbors;

            int neighbors_count = 0;
            for (int neighbor_id : neighbors) {
                if (neighbors_count >= max_neighbors_to_check) {
                    break; 
                }
                if (selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                    potential_neighbors.push_back(neighbor_id);
                }
                neighbors_count++;
            }

            if (!potential_neighbors.empty()) {
                candidate_customer = potential_neighbors[getRandomNumber(0, potential_neighbors.size() - 1)];
            }
        }

        if (candidate_customer == -1) {
            int attempts = 0;
            while (attempts < 1000) {
                int c_rand = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(c_rand) == selected_customers_set.end()) {
                    candidate_customer = c_rand;
                    break;
                }
                attempts++;
            }
            if (candidate_customer == -1) {
                break;
            }
        }

        selected_customers_set.insert(candidate_customer);
        selected_customers_list.push_back(candidate_customer);
    }

    return selected_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float w_prize = getRandomFraction(0.2f, 0.5f);
    float w_demand = getRandomFraction(0.1f, 0.3f);
    float w_depot_dist = getRandomFraction(0.1f, 0.3f);
    float w_random = getRandomFraction(0.01f, 0.1f);

    std::vector<std::pair<float, int>> customer_scores;

    for (int customer_id : customers) {
        float score = 0.0f;

        score += w_prize * instance.prizes[customer_id];

        score += w_demand * (1.0f / (1.0f + instance.demand[customer_id]));

        score += w_depot_dist * (1.0f / (1.0f + instance.distanceMatrix[0][customer_id]));

        score += w_random * getRandomFractionFast();

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}