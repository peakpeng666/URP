#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;
const int SELECT_MAX_NEIGHBORS_TO_CONSIDER = 10;

const float SORT_WEIGHT_DEMAND = 1.0f;
const float SORT_WEIGHT_DISTANCE_FROM_DEPOT = 0.5f;
const float SORT_STOCHASTIC_FACTOR = 0.1f;

std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) return {};

    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_customer);
    selected_customers_vec.push_back(initial_customer);

    while (selected_customers_set.size() < num_to_remove) {
        int expand_from_idx = getRandomNumber(0, selected_customers_vec.size() - 1);
        int current_seed_customer = selected_customers_vec[expand_from_idx];

        std::vector<int> candidate_neighbors;
        const auto& neighbors_of_seed = sol.instance.adj[current_seed_customer];

        for (size_t i = 0; i < neighbors_of_seed.size() && i < SELECT_MAX_NEIGHBORS_TO_CONSIDER; ++i) {
            int neighbor_id = neighbors_of_seed[i];
            if (neighbor_id != 0 && selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                candidate_neighbors.push_back(neighbor_id);
            }
        }

        if (!candidate_neighbors.empty()) {
            int chosen_neighbor_idx = getRandomNumber(0, candidate_neighbors.size() - 1);
            int new_customer_to_add = candidate_neighbors[chosen_neighbor_idx];
            selected_customers_set.insert(new_customer_to_add);
            selected_customers_vec.push_back(new_customer_to_add);
        } else {
            int potential_fallback_customer = -1;
            int attempts = 0;
            const int MAX_FALLBACK_ATTEMPTS = sol.instance.numCustomers * 2; 
            while (attempts < MAX_FALLBACK_ATTEMPTS) {
                int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(rand_cust) == selected_customers_set.end()) {
                    potential_fallback_customer = rand_cust;
                    break;
                }
                attempts++;
            }

            if (potential_fallback_customer != -1) {
                selected_customers_set.insert(potential_fallback_customer);
                selected_customers_vec.push_back(potential_fallback_customer);
            } else {
                break; 
            }
        }
    }
    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::sort(customers.begin(), customers.end(), [&](int cust_a, int cust_b) {
        float score_a = (float)instance.demand[cust_a] * SORT_WEIGHT_DEMAND + 
                        instance.distanceMatrix[0][cust_a] * SORT_WEIGHT_DISTANCE_FROM_DEPOT +
                        getRandomFractionFast() * SORT_STOCHASTIC_FACTOR;

        float score_b = (float)instance.demand[cust_b] * SORT_WEIGHT_DEMAND + 
                        instance.distanceMatrix[0][cust_b] * SORT_WEIGHT_DISTANCE_FROM_DEPOT +
                        getRandomFractionFast() * SORT_STOCHASTIC_FACTOR;
        
        return score_a > score_b;
    });
}