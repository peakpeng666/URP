#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>
#include "Utils.h"

static thread_local std::mt19937 rng_gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(5, 25);
    if (numCustomersToRemove == 0) return {};

    if (sol.instance.numCustomers == 0) return {};

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer);

    std::vector<int> candidates_vec;
    std::unordered_set<int> candidates_set;

    for (int neighbor : sol.instance.adj[seed_customer]) {
        if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
            if (candidates_set.find(neighbor) == candidates_set.end()) {
                candidates_vec.push_back(neighbor);
                candidates_set.insert(neighbor);
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidates_vec.empty()) {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
                selectedCustomers.insert(randomCustomer);
                for (int neighbor : sol.instance.adj[randomCustomer]) {
                    if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                        if (candidates_set.find(neighbor) == candidates_set.end()) {
                            candidates_vec.push_back(neighbor);
                            candidates_set.insert(neighbor);
                        }
                    }
                }
            }
            continue;
        }

        std::uniform_int_distribution<> dist(0, candidates_vec.size() - 1);
        int idx_to_pick = dist(rng_gen);
        int next_customer = candidates_vec[idx_to_pick];

        candidates_vec[idx_to_pick] = candidates_vec.back();
        candidates_vec.pop_back();
        candidates_set.erase(next_customer);

        selectedCustomers.insert(next_customer);

        for (int neighbor : sol.instance.adj[next_customer]) {
            if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                if (candidates_set.find(neighbor) == candidates_set.end()) {
                    candidates_vec.push_back(neighbor);
                    candidates_set.insert(neighbor);
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

    std::uniform_int_distribution<> strategy_dist(0, 3);
    int sort_type = strategy_dist(rng_gen);

    if (sort_type == 0) {
        std::shuffle(customers.begin(), customers.end(), rng_gen);
    } else if (sort_type == 1) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.prizes[c1] > instance.prizes[c2];
        });
    } else if (sort_type == 2) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] < instance.distanceMatrix[0][c2];
        });
    } else if (sort_type == 3) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float dist1 = instance.distanceMatrix[0][c1];
            float dist2 = instance.distanceMatrix[0][c2];
            float ratio1 = (dist1 > 1e-6) ? instance.prizes[c1] / dist1 : instance.prizes[c1] * 1e6;
            float ratio2 = (dist2 > 1e-6) ? instance.prizes[c2] / dist2 : instance.prizes[c2] * 1e6;
            return ratio1 > ratio2;
        });
    }
}