#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>
#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 20;
const int MAX_CUSTOMERS_TO_REMOVE = 50;
const int ADJ_LIST_CONSIDERATION_LIMIT = 20; // Number of closest neighbors to consider for expansion

const float DEMAND_WEIGHT = 100.0f;
const float DISTANCE_DEPOT_WEIGHT = 1.0f;
const int SORT_TOP_K_CONSIDERATION = 10;
const float STOCHASTIC_PICK_POWER = 2.0f;

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomers = sol.instance.numCustomers;
    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    if (numCustomersToRemove > numCustomers) {
        numCustomersToRemove = numCustomers;
    }

    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_list;

    int current_customer_id = getRandomNumber(1, numCustomers);
    selected_customers_set.insert(current_customer_id);
    selected_customers_list.push_back(current_customer_id);

    while (selected_customers_list.size() < numCustomersToRemove) {
        bool found_next = false;
        
        int num_neighbors_to_consider = std::min((int)sol.instance.adj[current_customer_id].size(), ADJ_LIST_CONSIDERATION_LIMIT);

        std::vector<int> valid_neighbors_candidates;
        for (int i = 0; i < num_neighbors_to_consider; ++i) {
            int neighbor_id = sol.instance.adj[current_customer_id][i];
            if (neighbor_id != 0 && selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                valid_neighbors_candidates.push_back(neighbor_id);
            }
        }

        if (!valid_neighbors_candidates.empty()) {
            int pick_idx = static_cast<int>(std::pow(getRandomFractionFast(), STOCHASTIC_PICK_POWER) * valid_neighbors_candidates.size());
            int next_customer_to_add = valid_neighbors_candidates[pick_idx];
            
            current_customer_id = next_customer_to_add;
            selected_customers_set.insert(current_customer_id);
            selected_customers_list.push_back(current_customer_id);
            found_next = true;
        }

        if (!found_next) {
            int fallback_customer_id = getRandomNumber(1, numCustomers);
            while (selected_customers_set.find(fallback_customer_id) != selected_customers_set.end()) {
                fallback_customer_id = getRandomNumber(1, numCustomers);
            }
            current_customer_id = fallback_customer_id;
            selected_customers_set.insert(current_customer_id);
            selected_customers_list.push_back(current_customer_id);
        }
    }
    return selected_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<int> current_customers_to_sort = customers;
    customers.clear();

    while (!current_customers_to_sort.empty()) {
        std::vector<std::pair<float, int>> scored_candidates;
        for (int customer_id : current_customers_to_sort) {
            float score = instance.demand[customer_id] * DEMAND_WEIGHT + 
                          instance.distanceMatrix[0][customer_id] * DISTANCE_DEPOT_WEIGHT;
            scored_candidates.push_back({score, customer_id});
        }

        std::sort(scored_candidates.rbegin(), scored_candidates.rend());

        int num_top_to_consider = std::min((int)scored_candidates.size(), SORT_TOP_K_CONSIDERATION);
        int pick_idx_in_top = static_cast<int>(std::pow(getRandomFractionFast(), STOCHASTIC_PICK_POWER) * num_top_to_consider);
        
        int chosen_customer_id = scored_candidates[pick_idx_in_top].second;

        customers.push_back(chosen_customer_id);

        auto it = std::remove(current_customers_to_sort.begin(), current_customers_to_sort.end(), chosen_customer_id);
        current_customers_to_sort.erase(it, current_customers_to_sort.end());
    }
}