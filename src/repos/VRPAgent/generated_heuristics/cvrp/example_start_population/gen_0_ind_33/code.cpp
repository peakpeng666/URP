#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits> // For std::numeric_limits
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(sol.instance.numCustomers / 100 * 3, sol.instance.numCustomers / 100 * 5);
    if (numCustomersToRemove < 10) numCustomersToRemove = 10;
    if (numCustomersToRemove > 50) numCustomersToRemove = 50;

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int start_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(start_customer);
    selectedCustomersVec.push_back(start_customer);

    float exploration_rate = 0.18f;
    int max_neighbor_check = 8;

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool added_customer_this_iter = false;

        if (getRandomFractionFast() < exploration_rate) {
            int new_customer_candidate = -1;
            for (int attempt = 0; attempt < sol.instance.numCustomers * 2; ++attempt) {
                int c_id = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(c_id) == selectedCustomersSet.end()) {
                    new_customer_candidate = c_id;
                    break;
                }
            }
            if (new_customer_candidate != -1) {
                selectedCustomersSet.insert(new_customer_candidate);
                selectedCustomersVec.push_back(new_customer_candidate);
                added_customer_this_iter = true;
            }
        }

        if (!added_customer_this_iter && selectedCustomersSet.size() < numCustomersToRemove) {
            int customer_from_set_idx = getRandomNumber(0, selectedCustomersVec.size() - 1);
            int customer_from_set = selectedCustomersVec[customer_from_set_idx];

            for (int i = 0; i < sol.instance.adj[customer_from_set].size() && i < max_neighbor_check; ++i) {
                int neighbor_node = sol.instance.adj[customer_from_set][i];
                if (neighbor_node == 0) continue;
                if (selectedCustomersSet.find(neighbor_node) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(neighbor_node);
                    selectedCustomersVec.push_back(neighbor_node);
                    added_customer_this_iter = true;
                    break;
                }
            }
        }

        if (!added_customer_this_iter && selectedCustomersSet.size() < numCustomersToRemove) {
            int fallback_customer = -1;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                    fallback_customer = i;
                    break;
                }
            }
            if (fallback_customer != -1) {
                selectedCustomersSet.insert(fallback_customer);
                selectedCustomersVec.push_back(fallback_customer);
            } else {
                break;
            }
        }
    }
    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<int> reinsertion_order;
    reinsertion_order.reserve(customers.size());

    std::unordered_set<int> remaining_customers_set(customers.begin(), customers.end());

    int first_customer = -1;
    float best_score = -1.0f;

    for (int c_id : customers) {
        float score = instance.distanceMatrix[0][c_id] + (float)instance.demand[c_id] * 0.1f;
        score += getRandomFractionFast() * 10.0f;

        if (score > best_score) {
            best_score = score;
            first_customer = c_id;
        }
    }

    if (first_customer != -1) {
        reinsertion_order.push_back(first_customer);
        remaining_customers_set.erase(first_customer);
    } else {
        return; 
    }

    while (!remaining_customers_set.empty()) {
        int next_customer_to_add = -1;
        float min_dist_to_order = std::numeric_limits<float>::max();

        for (int current_removed_customer : remaining_customers_set) {
            float dist_to_order = std::numeric_limits<float>::max();
            for (int ordered_customer : reinsertion_order) {
                float d = instance.distanceMatrix[ordered_customer][current_removed_customer];
                if (d < dist_to_order) {
                    dist_to_order = d;
                }
            }
            
            dist_to_order += getRandomFractionFast() * 0.1f;

            if (dist_to_order < min_dist_to_order) {
                min_dist_to_order = dist_to_order;
                next_customer_to_add = current_removed_customer;
            }
        }

        if (next_customer_to_add != -1) {
            reinsertion_order.push_back(next_customer_to_add);
            remaining_customers_set.erase(next_customer_to_add);
        } else {
            break;
        }
    }
    customers = reinsertion_order;
}