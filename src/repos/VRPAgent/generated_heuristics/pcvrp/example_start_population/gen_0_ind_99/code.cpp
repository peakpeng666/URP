#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

std::vector<int> get_visited_customers_impl(const Solution& sol) {
    std::vector<int> visited;
    visited.reserve(sol.instance.numCustomers);
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            visited.push_back(i);
        }
    }
    return visited;
}

std::vector<int> get_unvisited_customers_impl(const Solution& sol) {
    std::vector<int> unvisited;
    unvisited.reserve(sol.instance.numCustomers);
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] == -1) {
            unvisited.push_back(i);
        }
    }
    return unvisited;
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(20, 40);
    std::unordered_set<int> selectedCustomers;
    std::vector<int> frontierCandidates;

    std::vector<int> all_customers_idx;
    all_customers_idx.reserve(sol.instance.numCustomers);
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        all_customers_idx.push_back(i);
    }

    std::vector<int> visited_customers = get_visited_customers_impl(sol);
    std::vector<int> unvisited_customers = get_unvisited_customers_impl(sol);

    int seed_customer = -1;
    bool use_unvisited_seed = getRandomFraction() < 0.2;

    if (use_unvisited_seed && !unvisited_customers.empty()) {
        seed_customer = unvisited_customers[getRandomNumber(0, unvisited_customers.size() - 1)];
    } else if (!visited_customers.empty()) {
        seed_customer = visited_customers[getRandomNumber(0, visited_customers.size() - 1)];
    } else {
        seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    }

    selectedCustomers.insert(seed_customer);

    int k_neighbors_to_add = 5; 
    int neighbors_added_count = 0;
    for (int neighbor_idx : sol.instance.adj[seed_customer]) {
        if (selectedCustomers.find(neighbor_idx) == selectedCustomers.end() && neighbor_idx != seed_customer) {
            frontierCandidates.push_back(neighbor_idx);
            neighbors_added_count++;
        }
        if (neighbors_added_count >= k_neighbors_to_add) break; 
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        int current_customer_to_add = -1;

        if (!frontierCandidates.empty()) {
            int rand_idx = getRandomNumber(0, frontierCandidates.size() - 1);
            current_customer_to_add = frontierCandidates[rand_idx];
            
            frontierCandidates[rand_idx] = frontierCandidates.back();
            frontierCandidates.pop_back();

            if (selectedCustomers.count(current_customer_to_add)) {
                continue; 
            }
        } else {
            std::vector<int> unselected_global;
            unselected_global.reserve(all_customers_idx.size());
            for (int cust_id : all_customers_idx) {
                if (selectedCustomers.find(cust_id) == selectedCustomers.end()) {
                    unselected_global.push_back(cust_id);
                }
            }
            if (unselected_global.empty()) break; 
            current_customer_to_add = unselected_global[getRandomNumber(0, unselected_global.size() - 1)];
        }

        selectedCustomers.insert(current_customer_to_add);

        neighbors_added_count = 0;
        for (int neighbor_idx : sol.instance.adj[current_customer_to_add]) {
            if (selectedCustomers.find(neighbor_idx) == selectedCustomers.end() && neighbor_idx != current_customer_to_add) {
                frontierCandidates.push_back(neighbor_idx);
                neighbors_added_count++;
            }
            if (neighbors_added_count >= k_neighbors_to_add) break;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float rand_val = getRandomFraction();

    if (rand_val < 0.50) { 
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    } else if (rand_val < 0.70) { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.prizes[c1] > instance.prizes[c2];
        });
    } else if (rand_val < 0.90) { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] < instance.distanceMatrix[0][c2];
        });
    } else { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.adj[c1].size() > instance.adj[c2].size();
        });
    }
}