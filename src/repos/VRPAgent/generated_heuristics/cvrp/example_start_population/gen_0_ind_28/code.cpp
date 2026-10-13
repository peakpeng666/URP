#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int minCustomersToRemove = std::max(10, static_cast<int>(sol.instance.numCustomers * 0.02));
    int maxCustomersToRemove = std::min(40, static_cast<int>(sol.instance.numCustomers * 0.06));
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    std::unordered_set<int> selected_set;
    std::vector<int> selected_list;

    std::vector<int> potential_next_customers;
    std::unordered_set<int> potential_next_customers_set;

    const int k_neighbors_to_add = 7;

    int start_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(start_customer);
    selected_list.push_back(start_customer);

    int neighbors_added_from_seed = 0;
    for (int neighbor_idx : sol.instance.adj[start_customer]) {
        if (neighbor_idx == 0) continue; 
        
        if (neighbor_idx < 1 || neighbor_idx > sol.instance.numCustomers) continue;

        if (selected_set.find(neighbor_idx) == selected_set.end() && 
            potential_next_customers_set.find(neighbor_idx) == potential_next_customers_set.end()) {
            potential_next_customers.push_back(neighbor_idx);
            potential_next_customers_set.insert(neighbor_idx);
            neighbors_added_from_seed++;
        }
        if (neighbors_added_from_seed >= k_neighbors_to_add) break;
    }

    while (selected_list.size() < numCustomersToRemove) {
        if (potential_next_customers.empty()) {
            int fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            while (selected_set.count(fallback_customer)) {
                fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selected_set.insert(fallback_customer);
            selected_list.push_back(fallback_customer);

            int neighbors_added_from_fallback = 0;
            for (int neighbor_idx : sol.instance.adj[fallback_customer]) {
                if (neighbor_idx == 0) continue;
                if (neighbor_idx < 1 || neighbor_idx > sol.instance.numCustomers) continue;

                if (selected_set.find(neighbor_idx) == selected_set.end() &&
                    potential_next_customers_set.find(neighbor_idx) == potential_next_customers_set.end()) {
                    potential_next_customers.push_back(neighbor_idx);
                    potential_next_customers_set.insert(neighbor_idx);
                    neighbors_added_from_fallback++;
                }
                if (neighbors_added_from_fallback >= k_neighbors_to_add) break;
            }
            continue;
        }

        int candidate_idx = getRandomNumber(0, potential_next_customers.size() - 1);
        int next_customer_to_add = potential_next_customers[candidate_idx];

        potential_next_customers[candidate_idx] = potential_next_customers.back();
        potential_next_customers.pop_back();
        potential_next_customers_set.erase(next_customer_to_add);

        if (selected_set.find(next_customer_to_add) == selected_set.end()) {
            selected_set.insert(next_customer_to_add);
            selected_list.push_back(next_customer_to_add);

            int neighbors_added_from_current = 0;
            for (int neighbor_idx : sol.instance.adj[next_customer_to_add]) {
                if (neighbor_idx == 0) continue;
                if (neighbor_idx < 1 || neighbor_idx > sol.instance.numCustomers) continue;

                if (selected_set.find(neighbor_idx) == selected_set.end() && 
                    potential_next_customers_set.find(neighbor_idx) == potential_next_customers_set.end()) {
                    potential_next_customers.push_back(neighbor_idx);
                    potential_next_customers_set.insert(neighbor_idx);
                    neighbors_added_from_current++;
                }
                if (neighbors_added_from_current >= k_neighbors_to_add) break;
            }
        }
    }
    return selected_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float distance_from_depot = instance.distanceMatrix[0][customer_id];
        customer_scores.push_back({distance_from_depot, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }

    float swap_probability = 0.15f;

    for (size_t i = 0; i < customers.size() - 1; ++i) {
        if (getRandomFractionFast() < swap_probability) {
            std::swap(customers[i], customers[i+1]);
        }
    }
}