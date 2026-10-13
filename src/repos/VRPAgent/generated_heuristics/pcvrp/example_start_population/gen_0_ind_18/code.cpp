#include "AgentDesigned.h"
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    int num_to_remove = getRandomNumber(10, 20);

    std::vector<int> candidate_pool;
    std::unordered_set<int> candidate_pool_set;

    const int MAX_CANDIDATE_POOL_SIZE = 200;
    const int NEIGHBORS_TO_CONSIDER = 5;

    int num_initial_seeds = getRandomNumber(1, 3);
    for (int i = 0; i < num_initial_seeds && selected_customers_set.size() < num_to_remove; ++i) {
        int customer_id = getRandomNumber(1, instance.numCustomers);
        if (selected_customers_set.find(customer_id) == selected_customers_set.end()) {
            selected_customers_set.insert(customer_id);
            selected_customers_vec.push_back(customer_id);

            for (size_t j = 0; j < instance.adj[customer_id].size() && j < NEIGHBORS_TO_CONSIDER; ++j) {
                int neighbor_id = instance.adj[customer_id][j];
                if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                    candidate_pool_set.find(neighbor_id) == candidate_pool_set.end() &&
                    candidate_pool.size() < MAX_CANDIDATE_POOL_SIZE) {
                    candidate_pool.push_back(neighbor_id);
                    candidate_pool_set.insert(neighbor_id);
                }
            }
        }
    }

    while (selected_customers_set.size() < num_to_remove) {
        int customer_to_add = -1;

        if (getRandomFractionFast() < 0.15) {
            int random_cand = getRandomNumber(1, instance.numCustomers);
            if (selected_customers_set.find(random_cand) == selected_customers_set.end() &&
                candidate_pool_set.find(random_cand) == candidate_pool_set.end() &&
                candidate_pool.size() < MAX_CANDIDATE_POOL_SIZE) {
                candidate_pool.push_back(random_cand);
                candidate_pool_set.insert(random_cand);
            }
        }

        if (getRandomFractionFast() < 0.2) {
            for (int i = 0; i < 10; ++i) {
                int probe_cust_id = getRandomNumber(1, instance.numCustomers);
                if (sol.customerToTourMap[probe_cust_id] == -1 &&
                    selected_customers_set.find(probe_cust_id) == selected_customers_set.end() &&
                    candidate_pool_set.find(probe_cust_id) == candidate_pool_set.end() &&
                    candidate_pool.size() < MAX_CANDIDATE_POOL_SIZE) {
                    candidate_pool.push_back(probe_cust_id);
                    candidate_pool_set.insert(probe_cust_id);
                    break;
                }
            }
        }

        if (candidate_pool.empty()) {
            customer_to_add = getRandomNumber(1, instance.numCustomers);
            while (selected_customers_set.find(customer_to_add) != selected_customers_set.end()) {
                customer_to_add = getRandomNumber(1, instance.numCustomers);
            }
        } else {
            std::vector<std::pair<float, int>> scored_candidates;
            scored_candidates.reserve(candidate_pool.size());

            for (int cand_id : candidate_pool) {
                if (selected_customers_set.find(cand_id) != selected_customers_set.end()) {
                    continue;
                }
                float min_dist_to_selected = std::numeric_limits<float>::max();
                for (int sel_id : selected_customers_set) {
                    min_dist_to_selected = std::min(min_dist_to_selected, instance.distanceMatrix[sel_id][cand_id]);
                }
                float score = 1.0f / (min_dist_to_selected + 0.01f) + getRandomFractionFast() * 0.1f;
                scored_candidates.push_back({score, cand_id});
            }

            if (scored_candidates.empty()) {
                customer_to_add = getRandomNumber(1, instance.numCustomers);
                while (selected_customers_set.find(customer_to_add) != selected_customers_set.end()) {
                    customer_to_add = getRandomNumber(1, instance.numCustomers);
                }
            } else {
                std::sort(scored_candidates.rbegin(), scored_candidates.rend());

                int k_sample = std::min((int)scored_candidates.size(), 5);
                customer_to_add = scored_candidates[getRandomNumber(0, k_sample - 1)].second;
            }
        }

        if (customer_to_add != -1 && selected_customers_set.find(customer_to_add) == selected_customers_set.end()) {
            selected_customers_set.insert(customer_to_add);
            selected_customers_vec.push_back(customer_to_add);

            for (size_t j = 0; j < instance.adj[customer_to_add].size() && j < NEIGHBORS_TO_CONSIDER; ++j) {
                int neighbor_id = instance.adj[customer_to_add][j];
                if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                    candidate_pool_set.find(neighbor_id) == candidate_pool_set.end() &&
                    candidate_pool.size() < MAX_CANDIDATE_POOL_SIZE) {
                    candidate_pool.push_back(neighbor_id);
                    candidate_pool_set.insert(neighbor_id);
                }
            }
        }
    }
    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id];

        float score = prize / (dist_to_depot + 0.01f);

        score += getRandomFractionFast() * 0.1f;

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.rbegin(), scored_customers.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}