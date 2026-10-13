#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>
#include <limits>

#include "Utils.h"
#include "Solution.h"
#include "Instance.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(20, 40);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    if (numCustomersToRemove == 0) {
        return {};
    }

    std::vector<int> candidates_queue;
    std::unordered_set<int> candidates_set;

    int initial_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initial_customer_idx);

    const auto& adj_list_initial = sol.instance.adj[initial_customer_idx];
    for (size_t i = 0; i < std::min((size_t)10, adj_list_initial.size()); ++i) {
        int neighbor_id = adj_list_initial[i];
        if (selectedCustomers.find(neighbor_id) == selectedCustomers.end() && candidates_set.find(neighbor_id) == candidates_set.end()) {
            candidates_queue.push_back(neighbor_id);
            candidates_set.insert(neighbor_id);
        }
    }
    static thread_local std::mt19937 gen_select(std::random_device{}());
    std::shuffle(candidates_queue.begin(), candidates_queue.end(), gen_select);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int current_customer_to_add = -1;

        if (!candidates_queue.empty()) {
            int rand_idx = getRandomNumber(0, candidates_queue.size() - 1);
            current_customer_to_add = candidates_queue[rand_idx];
            
            std::swap(candidates_queue[rand_idx], candidates_queue.back());
            candidates_queue.pop_back();
            candidates_set.erase(current_customer_to_add);
        } else {
            int attempts = 0;
            while (current_customer_to_add == -1 && attempts < sol.instance.numCustomers * 2) {
                int rand_customer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(rand_customer) == selectedCustomers.end()) {
                    current_customer_to_add = rand_customer;
                }
                attempts++;
            }
            if (current_customer_to_add == -1) {
                break;
            }
        }

        if (selectedCustomers.find(current_customer_to_add) == selectedCustomers.end()) {
            selectedCustomers.insert(current_customer_to_add);

            const auto& adj_list_current = sol.instance.adj[current_customer_to_add];
            for (size_t i = 0; i < std::min((size_t)10, adj_list_current.size()); ++i) {
                int neighbor_id = adj_list_current[i];
                if (selectedCustomers.find(neighbor_id) == selectedCustomers.end() && candidates_set.find(neighbor_id) == candidates_set.end()) {
                    candidates_queue.push_back(neighbor_id);
                    candidates_set.insert(neighbor_id);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    std::unordered_set<int> removed_customers_set(customers.begin(), customers.end());

    for (int customer_id : customers) {
        float demand_score = static_cast<float>(instance.demand[customer_id]);

        float connectivity_score = 0.0f;
        const auto& adj_list_customer = instance.adj[customer_id];
        for (size_t i = 0; i < std::min((size_t)10, adj_list_customer.size()); ++i) {
            int neighbor_id = adj_list_customer[i];
            if (removed_customers_set.count(neighbor_id)) {
                connectivity_score += 1.0f; 
            }
        }
        
        float final_score = demand_score * 0.5f + connectivity_score * 0.5f + getRandomFractionFast() * 0.001f;

        customer_scores.emplace_back(final_score, customer_id);
    }

    std::sort(customer_scores.begin(), customer_scores.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}