#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include "Utils.h"
#include <algorithm>
#include <vector>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_list;

    int num_to_remove = getRandomNumber(10, 20);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(initial_customer_id);
    selected_list.push_back(initial_customer_id);

    while (selected_set.size() < num_to_remove) {
        bool found_new_customer_from_neighborhood = false;
        
        for (int attempt = 0; attempt < selected_list.size() * 2 && !found_new_customer_from_neighborhood; ++attempt) {
            int current_selected_idx = getRandomNumber(0, selected_list.size() - 1);
            int seed_customer = selected_list[current_selected_idx];

            std::vector<int> eligible_neighbors;
            for (int neighbor : sol.instance.adj[seed_customer]) {
                if (selected_set.find(neighbor) == selected_set.end()) {
                    eligible_neighbors.push_back(neighbor);
                }
            }

            if (!eligible_neighbors.empty()) {
                int new_customer = eligible_neighbors[getRandomNumber(0, eligible_neighbors.size() - 1)];
                selected_set.insert(new_customer);
                selected_list.push_back(new_customer);
                found_new_customer_from_neighborhood = true;
            }
        }

        if (!found_new_customer_from_neighborhood) {
            int random_customer;
            do {
                random_customer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selected_set.count(random_customer)); 

            selected_set.insert(random_customer);
            selected_list.push_back(random_customer);
        }
    }

    return selected_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance, const Solution& sol) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    float noise_epsilon = 1.0; 
    float unvisited_boost = 100.0; 

    for (int customer_id : customers) {
        float base_score = instance.prizes[customer_id] - instance.distanceMatrix[0][customer_id];

        base_score += getRandomFraction(-noise_epsilon, noise_epsilon);

        if (sol.customerToTourMap[customer_id] == -1) {
            base_score += unvisited_boost;
        }
        scored_customers.push_back({base_score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}