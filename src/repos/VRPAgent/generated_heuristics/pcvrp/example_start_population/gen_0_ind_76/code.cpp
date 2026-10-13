#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"
#include <limits>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    int num_to_remove = std::max(5, getRandomNumber(sol.instance.numCustomers / 50, sol.instance.numCustomers / 20));
    num_to_remove = std::min(num_to_remove, sol.instance.numCustomers);

    std::vector<int> visited_customers_in_solution;
    for (const Tour& tour : sol.tours) {
        for (int customer_id : tour.customers) {
            visited_customers_in_solution.push_back(customer_id);
        }
    }

    std::vector<int> candidates_pool;

    int initial_seed = -1;
    if (!visited_customers_in_solution.empty()) {
        initial_seed = visited_customers_in_solution[getRandomNumber(0, visited_customers_in_solution.size() - 1)];
    } else {
        initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    }

    selected_customers_set.insert(initial_seed);
    selected_customers_vec.push_back(initial_seed);

    if (sol.customerToTourMap[initial_seed] != -1) {
        int tour_idx = sol.customerToTourMap[initial_seed];
        for (int customer_in_tour : sol.tours[tour_idx].customers) {
            if (customer_in_tour != initial_seed) {
                candidates_pool.push_back(customer_in_tour);
            }
        }
    }

    int k_geo_neighbors = 5;
    for (size_t i = 0; i < std::min((size_t)k_geo_neighbors, sol.instance.adj[initial_seed].size()); ++i) {
        int neighbor_id = sol.instance.adj[initial_seed][i];
        if (neighbor_id != initial_seed) {
            candidates_pool.push_back(neighbor_id);
        }
    }

    while (selected_customers_set.size() < num_to_remove) {
        if (candidates_pool.empty()) {
            std::vector<int> unselected_global_customers;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (!selected_customers_set.count(i)) {
                    unselected_global_customers.push_back(i);
                }
            }

            if (unselected_global_customers.empty()) {
                break;
            }

            int new_seed = unselected_global_customers[getRandomNumber(0, unselected_global_customers.size() - 1)];
            selected_customers_set.insert(new_seed);
            selected_customers_vec.push_back(new_seed);

            if (sol.customerToTourMap[new_seed] != -1) {
                int tour_idx = sol.customerToTourMap[new_seed];
                for (int customer_in_tour : sol.tours[tour_idx].customers) {
                    if (!selected_customers_set.count(customer_in_tour)) {
                        candidates_pool.push_back(customer_in_tour);
                    }
                }
            }
            for (size_t i = 0; i < std::min((size_t)k_geo_neighbors, sol.instance.adj[new_seed].size()); ++i) {
                int neighbor_id = sol.instance.adj[new_seed][i];
                if (!selected_customers_set.count(neighbor_id)) {
                    candidates_pool.push_back(neighbor_id);
                }
            }
            continue;
        }

        int rand_idx = getRandomNumber(0, candidates_pool.size() - 1);
        int current_candidate = candidates_pool[rand_idx];

        if (rand_idx != candidates_pool.size() - 1) {
            candidates_pool[rand_idx] = candidates_pool.back();
        }
        candidates_pool.pop_back();

        if (selected_customers_set.count(current_candidate)) {
            continue;
        }

        selected_customers_set.insert(current_candidate);
        selected_customers_vec.push_back(current_candidate);

        if (sol.customerToTourMap[current_candidate] != -1) {
            int tour_idx = sol.customerToTourMap[current_candidate];
            for (int customer_in_tour : sol.tours[tour_idx].customers) {
                if (!selected_customers_set.count(customer_in_tour)) {
                    candidates_pool.push_back(customer_in_tour);
                }
            }
        }
        for (size_t i = 0; i < std::min((size_t)k_geo_neighbors, sol.instance.adj[current_candidate].size()); ++i) {
            int neighbor_id = sol.instance.adj[current_candidate][i];
            if (!selected_customers_set.count(neighbor_id)) {
                candidates_pool.push_back(neighbor_id);
            }
        }
    }

    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    float prize_weight = 1.0;
    float distance_weight = 0.05;
    float noise_magnitude = 0.001;

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id] * prize_weight;
        score -= instance.distanceMatrix[0][customer_id] * distance_weight;
        score += getRandomFractionFast() * noise_magnitude;

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}