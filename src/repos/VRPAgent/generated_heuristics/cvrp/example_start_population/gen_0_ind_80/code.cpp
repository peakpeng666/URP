#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <numeric>
#include "Utils.h"

// Using a static thread_local random number generator for performance and thread safety
static thread_local std::mt19937 random_gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int minCustomersToRemove = 5;
    int maxCustomersToRemove = 20;
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        numCustomersToRemove = 1;
    }

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> current_candidates;
        for (int sc_id : selectedCustomers) {
            int max_adj_neighbors_to_consider = std::min((int)sol.instance.adj[sc_id].size(), 10);
            for (int i = 0; i < max_adj_neighbors_to_consider; ++i) {
                int neighbor = sol.instance.adj[sc_id][i];
                if (neighbor != 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    current_candidates.push_back(neighbor);
                }
            }
        }

        if (current_candidates.empty()) {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            selectedCustomers.insert(randomCustomer);
        } else {
            int idx_to_add = getRandomNumber(0, (int)current_candidates.size() - 1);
            selectedCustomers.insert(current_candidates[idx_to_add]);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::sort(customers.begin(), customers.end(), [&](int a, int b) {
        return instance.demand[a] > instance.demand[b];
    });

    int num_perturbations = std::min((int)customers.size() / 2, 5);
    for (int i = 0; i < num_perturbations; ++i) {
        if (getRandomFractionFast() < 0.2) {
            if (customers.size() < 2) continue;
            int idx1 = getRandomNumber(0, (int)customers.size() - 2);
            int idx2 = idx1 + 1;
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}