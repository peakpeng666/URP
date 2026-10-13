#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    int numCustomers = sol.instance.numCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove == 0) {
        return {};
    }

    float p_random_global_select = 0.2f;

    int initial_seed_attempts = 0;
    while (selectedCustomersSet.empty() && initial_seed_attempts < 50) {
        int initial_seed = getRandomNumber(1, numCustomers);
        if (initial_seed != 0) {
            selectedCustomersSet.insert(initial_seed);
        }
        initial_seed_attempts++;
    }
    if (selectedCustomersSet.empty()) {
        return {};
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool added_customer_in_iteration = false;
        float r = getRandomFractionFast();

        if (r < p_random_global_select) {
            int attempts = 0;
            while (attempts < 50) {
                int customer_to_add = getRandomNumber(1, numCustomers);
                if (customer_to_add != 0 && selectedCustomersSet.find(customer_to_add) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(customer_to_add);
                    added_customer_in_iteration = true;
                    break;
                }
                attempts++;
            }
        } else {
            int attempts_base_customer = 0;
            while (attempts_base_customer < 10 && !added_customer_in_iteration) {
                int base_customer_candidate = getRandomNumber(1, numCustomers);
                if (selectedCustomersSet.count(base_customer_candidate)) {
                    int base_customer = base_customer_candidate;

                    const std::vector<int>& neighbors = sol.instance.adj[base_customer];
                    int num_neighbors_to_consider = std::min((int)neighbors.size(), 10);

                    if (num_neighbors_to_consider > 0) {
                        int neighbor_attempts = 0;
                        while (neighbor_attempts < 10) {
                            int neighbor_list_idx = getRandomNumber(0, num_neighbors_to_consider - 1);
                            int customer_to_add = neighbors[neighbor_list_idx];

                            if (customer_to_add != 0 && selectedCustomersSet.find(customer_to_add) == selectedCustomersSet.end()) {
                                selectedCustomersSet.insert(customer_to_add);
                                added_customer_in_iteration = true;
                                break;
                            }
                            neighbor_attempts++;
                        }
                    }
                }
                attempts_base_customer++;
            }
        }

        if (!added_customer_in_iteration && selectedCustomersSet.size() < numCustomersToRemove) {
            int attempts_fallback = 0;
            while (attempts_fallback < 50) {
                int customer_to_add = getRandomNumber(1, numCustomers);
                if (customer_to_add != 0 && selectedCustomersSet.find(customer_to_add) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(customer_to_add);
                    added_customer_in_iteration = true;
                    break;
                }
                attempts_fallback++;
            }
        }
    }
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float r_strategy = getRandomFractionFast();

    if (r_strategy < 0.33f) {
        std::vector<std::pair<float, int>> scored_customers;
        scored_customers.reserve(customers.size());
        for (int customer_id : customers) {
            float score = (float)instance.demand[customer_id] + getRandomFractionFast() * 0.01f;
            scored_customers.push_back({score, customer_id});
        }
        std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scored_customers[i].second;
        }
    } else if (r_strategy < 0.66f) {
        std::vector<std::pair<float, int>> scored_customers;
        scored_customers.reserve(customers.size());
        for (int customer_id : customers) {
            float score = instance.distanceMatrix[0][customer_id] + getRandomFractionFast() * 0.01f;
            scored_customers.push_back({score, customer_id});
        }
        std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scored_customers[i].second;
        }
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}