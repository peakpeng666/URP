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

    int num_to_remove = getRandomNumber(8, 25);

    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) {
        num_to_remove = 1;
    } else if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_customer);
    selected_customers_vec.push_back(initial_customer);

    const int MAX_ATTEMPTS_PER_ADD = 50;
    const int NEIGHBOR_CONSIDERATION_LIMIT = 15;

    int current_unsuccessful_attempts = 0;

    while (selected_customers_set.size() < num_to_remove && current_unsuccessful_attempts < num_to_remove * MAX_ATTEMPTS_PER_ADD) {
        int source_customer_idx = getRandomNumber(0, selected_customers_vec.size() - 1);
        int source_customer = selected_customers_vec[source_customer_idx];

        const auto& neighbors = sol.instance.adj[source_customer];
        if (neighbors.empty()) {
            current_unsuccessful_attempts++;
            continue;
        }

        bool customer_added_in_this_iter = false;
        int limit = std::min((int)neighbors.size(), NEIGHBOR_CONSIDERATION_LIMIT);
        if (limit == 0) { // Edge case if neighbors become empty due to min
             current_unsuccessful_attempts++;
             continue;
        }
        
        int start_neighbor_search_idx = getRandomNumber(0, limit - 1);
        
        for (int i = 0; i < limit; ++i) {
            int current_neighbor_list_idx = (start_neighbor_search_idx + i) % limit;
            int candidate_customer = neighbors[current_neighbor_list_idx];

            if (candidate_customer > 0 && selected_customers_set.find(candidate_customer) == selected_customers_set.end()) {
                selected_customers_set.insert(candidate_customer);
                selected_customers_vec.push_back(candidate_customer);
                customer_added_in_this_iter = true;
                break;
            }
        }

        if (!customer_added_in_this_iter) {
            current_unsuccessful_attempts++;
        } else {
            current_unsuccessful_attempts = 0;
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = static_cast<float>(instance.demand[customer_id]) + instance.distanceMatrix[0][customer_id];
        score += getRandomFractionFast() * 5.0f;

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.rbegin(), customer_scores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}