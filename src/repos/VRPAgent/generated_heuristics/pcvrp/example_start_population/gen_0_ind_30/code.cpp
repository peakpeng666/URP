#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> frontier_customers;

    int numCustomersToRemove = getRandomNumber(10, 20);

    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    } else if (sol.instance.numCustomers == 0) {
        return {};
    }

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(seed_customer);
    frontier_customers.push_back(seed_customer);

    while (selected_customers_set.size() < numCustomersToRemove) {
        if (frontier_customers.empty()) {
            int new_seed = -1;
            int attempts = 0;
            while (attempts < sol.instance.numCustomers * 2) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(potential_seed) == selected_customers_set.end()) {
                    new_seed = potential_seed;
                    break;
                }
                attempts++;
            }

            if (new_seed != -1) {
                selected_customers_set.insert(new_seed);
                frontier_customers.push_back(new_seed);
            } else {
                break;
            }
        }

        int rand_idx = getRandomNumber(0, frontier_customers.size() - 1);
        int current_seed = frontier_customers[rand_idx];

        bool expanded_this_round = false;
        for (int neighbor : sol.instance.adj[current_seed]) {
            if (neighbor == 0) continue; 

            if (selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                selected_customers_set.insert(neighbor);
                frontier_customers.push_back(neighbor);
                expanded_this_round = true;
                break;
            }
        }

        if (!expanded_this_round) {
            frontier_customers[rand_idx] = frontier_customers.back();
            frontier_customers.pop_back();
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());

    float r = getRandomFractionFast();

    if (r < 0.30) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.prizes[a] > instance.prizes[b];
        });
    } else if (r < 0.50) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] > instance.demand[b];
        });
    } else if (r < 0.70) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            float ratio_a = (instance.demand[a] == 0) ? std::numeric_limits<float>::max() : instance.prizes[a] / instance.demand[a];
            float ratio_b = (instance.demand[b] == 0) ? std::numeric_limits<float>::max() : instance.prizes[b] / instance.demand[b];
            return ratio_a > ratio_b;
        });
    } else if (r < 0.90) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
        });
    } else {
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}