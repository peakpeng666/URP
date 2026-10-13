#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort, std::swap
#include "Utils.h" // For getRandomNumber, getRandomFraction

// Heuristic for customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidate_pool;

    int numCustomersToRemove = getRandomNumber(15, 30);
    int numCustomersInInstance = sol.instance.numCustomers;
    int max_neighbors_to_add = 5;

    int initial_seed_customer = getRandomNumber(1, numCustomersInInstance);
    selectedCustomers.insert(initial_seed_customer);

    for (size_t i = 0; i < sol.instance.adj[initial_seed_customer].size() && i < max_neighbors_to_add; ++i) {
        int neighbor = sol.instance.adj[initial_seed_customer][i];
        if (neighbor >= 1 && neighbor <= numCustomersInInstance && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
            candidate_pool.push_back(neighbor);
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidate_pool.empty()) {
            int new_seed_attempts = 0;
            bool new_seed_found = false;
            while (new_seed_attempts < 100 && selectedCustomers.size() < numCustomersToRemove) {
                int new_seed = getRandomNumber(1, numCustomersInInstance);
                if (selectedCustomers.find(new_seed) == selectedCustomers.end()) {
                    selectedCustomers.insert(new_seed);
                    for (size_t i = 0; i < sol.instance.adj[new_seed].size() && i < max_neighbors_to_add; ++i) {
                        int neighbor = sol.instance.adj[new_seed][i];
                        if (neighbor >= 1 && neighbor <= numCustomersInInstance && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                            candidate_pool.push_back(neighbor);
                        }
                    }
                    new_seed_found = true;
                    break;
                }
                new_seed_attempts++;
            }
            if (!new_seed_found || selectedCustomers.size() >= numCustomersToRemove) {
                break;
            }
        }

        int idx_to_pick = getRandomNumber(0, candidate_pool.size() - 1);
        int customer_to_add = candidate_pool[idx_to_pick];

        std::swap(candidate_pool[idx_to_pick], candidate_pool.back());
        candidate_pool.pop_back();

        if (selectedCustomers.find(customer_to_add) == selectedCustomers.end()) {
            selectedCustomers.insert(customer_to_add);

            for (size_t i = 0; i < sol.instance.adj[customer_to_add].size() && i < max_neighbors_to_add; ++i) {
                int neighbor = sol.instance.adj[customer_to_add][i];
                if (neighbor >= 1 && neighbor <= numCustomersInInstance && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    candidate_pool.push_back(neighbor);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Heuristic for ordering of the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float random_selector = getRandomFraction();

    if (random_selector < 0.6) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.prizes[a] > instance.prizes[b];
        });
    } else if (random_selector < 0.9) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            float prize_a = instance.prizes[a];
            float demand_a = instance.demand[a];
            float ratio_a = demand_a > 0 ? prize_a / demand_a : prize_a; // Prioritize prize if demand is 0

            float prize_b = instance.prizes[b];
            float demand_b = instance.demand[b];
            float ratio_b = demand_b > 0 ? prize_b / demand_b : prize_b;

            return ratio_a > ratio_b;
        });
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}