#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::shuffle
#include <vector>    // For std::vector
#include <cmath>     // For std::max and std::min

#include "Utils.h"
#include "Solution.h"
#include "Instance.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;

    int numCustomersToRemove = getRandomNumber(std::max(5, sol.instance.numCustomers / 100), std::min(20, sol.instance.numCustomers / 25));

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer);

    int safety_counter = 0;
    const int MAX_SAFETY_ITERATIONS = numCustomersToRemove * 10;

    while (selectedCustomers.size() < numCustomersToRemove && safety_counter < MAX_SAFETY_ITERATIONS) {
        safety_counter++;

        std::vector<int> current_selected_vec(selectedCustomers.begin(), selectedCustomers.end());
        int anchor_customer_idx = getRandomNumber(0, current_selected_vec.size() - 1);
        int anchor_customer = current_selected_vec[anchor_customer_idx];

        const int K_MAX_ADJ_NEIGHBORS = 10;
        std::vector<int> candidates;

        for (int neighbor_node : sol.instance.adj[anchor_customer]) {
            if (neighbor_node != 0 && selectedCustomers.find(neighbor_node) == selectedCustomers.end()) {
                candidates.push_back(neighbor_node);
            }
            if (candidates.size() >= K_MAX_ADJ_NEIGHBORS) {
                break;
            }
        }

        if (!candidates.empty()) {
            int chosen_candidate_idx = getRandomNumber(0, candidates.size() - 1);
            selectedCustomers.insert(candidates[chosen_candidate_idx]);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float rand_val = getRandomFractionFast();

    if (rand_val < 0.2f) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
        });
    } else if (rand_val < 0.4f) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] > instance.distanceMatrix[0][b];
        });
    } else if (rand_val < 0.6f) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] > instance.demand[b];
        });
    } else if (rand_val < 0.9f) {
        int anchor_customer_idx = getRandomNumber(0, customers.size() - 1);
        int anchor_customer = customers[anchor_customer_idx];

        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[anchor_customer][a] < instance.distanceMatrix[anchor_customer][b];
        });
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}