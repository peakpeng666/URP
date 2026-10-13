#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    int numCustomers = instance.numCustomers;
    int target_remove_count = getRandomNumber(std::max(1, (int)(numCustomers * 0.04)), std::min(numCustomers, (int)(numCustomers * 0.08)));
    target_remove_count = std::min(target_remove_count, 50);

    std::unordered_set<int> selected_customers_set;
    std::vector<int> customers_to_process;

    int initial_customer = getRandomNumber(1, numCustomers);
    selected_customers_set.insert(initial_customer);
    customers_to_process.push_back(initial_customer);

    int head = 0;

    while (selected_customers_set.size() < target_remove_count && head < customers_to_process.size()) {
        int current_customer = customers_to_process[head++];

        int num_neighbors_to_consider = getRandomNumber(1, std::min(5, (int)instance.adj[current_customer].size()));

        for (int i = 0; i < num_neighbors_to_consider; ++i) {
            int neighbor = instance.adj[current_customer][i];
            if (selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                if (getRandomFraction() < 0.8) {
                    selected_customers_set.insert(neighbor);
                    customers_to_process.push_back(neighbor);
                    if (selected_customers_set.size() == target_remove_count) {
                        break;
                    }
                }
            }
        }

        if (head == customers_to_process.size() && selected_customers_set.size() < target_remove_count) {
            int new_seed = -1;
            int attempts = 0;
            while (new_seed == -1 || selected_customers_set.find(new_seed) != selected_customers_set.end()) {
                new_seed = getRandomNumber(1, numCustomers);
                attempts++;
                if (attempts > numCustomers * 2) {
                    break;
                }
                if (selected_customers_set.size() == numCustomers) {
                    break;
                }
            }
            if (new_seed != -1 && selected_customers_set.find(new_seed) == selected_customers_set.end()) {
                 selected_customers_set.insert(new_seed);
                 customers_to_process.push_back(new_seed);
            }
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (getRandomFraction() < 0.6) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            float startTW_a = instance.startTW[a];
            float TW_Width_a = instance.TW_Width[a];

            float startTW_b = instance.startTW[b];
            float TW_Width_b = instance.TW_Width[b];

            if (startTW_a != startTW_b) {
                return startTW_a < startTW_b;
            }
            if (TW_Width_a != TW_Width_b) {
                return TW_Width_a < TW_Width_b;
            }
            if (instance.demand[a] != instance.demand[b]) {
                return instance.demand[a] > instance.demand[b];
            }
            return a < b;
        });
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}