#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20);

    std::unordered_set<int> selected_customers_set;
    std::vector<int> result_customers_vec;
    std::unordered_set<int> candidate_pool_set;

    const int max_neighbors_to_consider = 5; 

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(seed_customer);
    result_customers_vec.push_back(seed_customer);

    for (int i = 0; i < std::min((int)sol.instance.adj[seed_customer].size(), max_neighbors_to_consider); ++i) {
        int neighbor = sol.instance.adj[seed_customer][i];
        if (neighbor > 0 && selected_customers_set.find(neighbor) == selected_customers_set.end()) {
            candidate_pool_set.insert(neighbor);
        }
    }

    while (result_customers_vec.size() < numCustomersToRemove) {
        if (candidate_pool_set.empty()) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            while (selected_customers_set.count(new_seed)) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selected_customers_set.insert(new_seed);
            result_customers_vec.push_back(new_seed);

            if (result_customers_vec.size() == numCustomersToRemove) {
                break;
            }

            for (int i = 0; i < std::min((int)sol.instance.adj[new_seed].size(), max_neighbors_to_consider); ++i) {
                int neighbor = sol.instance.adj[new_seed][i];
                if (neighbor > 0 && selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                    candidate_pool_set.insert(neighbor);
                }
            }
            continue;
        }

        std::vector<int> candidate_pool_vec(candidate_pool_set.begin(), candidate_pool_set.end());

        int idx = getRandomNumber(0, (int)candidate_pool_vec.size() - 1);
        int chosen_customer = candidate_pool_vec[idx];

        selected_customers_set.insert(chosen_customer);
        result_customers_vec.push_back(chosen_customer);

        candidate_pool_set.erase(chosen_customer);

        for (int i = 0; i < std::min((int)sol.instance.adj[chosen_customer].size(), max_neighbors_to_consider); ++i) {
            int neighbor = sol.instance.adj[chosen_customer][i];
            if (neighbor > 0 && selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                candidate_pool_set.insert(neighbor);
            }
        }
    }

    return result_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int criteria_type = getRandomNumber(0, 2);
    int sort_direction = getRandomNumber(0, 1);

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = 0.0f;
        switch (criteria_type) {
            case 0: {
                score = static_cast<float>(instance.demand[customer_id]);
                break;
            }
            case 1: {
                score = instance.distanceMatrix[customer_id][0];
                break;
            }
            case 2: {
                float sum_dist = 0.0f;
                int count = 0;
                for (int other_customer_id : customers) {
                    if (other_customer_id != customer_id) {
                        sum_dist += instance.distanceMatrix[customer_id][other_customer_id];
                        count++;
                    }
                }
                score = (count > 0) ? sum_dist / count : 0.0f;
                break;
            }
        }
        score += getRandomFractionFast() * 0.001f;
        customer_scores.push_back({score, customer_id});
    }

    if (sort_direction == 0) {
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });
    } else {
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}