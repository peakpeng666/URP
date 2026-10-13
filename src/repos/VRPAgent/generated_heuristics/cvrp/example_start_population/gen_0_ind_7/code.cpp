#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include "Utils.h"

static thread_local std::mt19937 gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;
    std::vector<int> selected_list;

    int num_to_remove = getRandomNumber(10, 20); 

    std::vector<int> candidates_for_expansion;

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    
    selected_set.insert(seed_customer);
    selected_list.push_back(seed_customer);
    candidates_for_expansion.push_back(seed_customer);

    while (selected_list.size() < num_to_remove) {
        if (candidates_for_expansion.empty()) {
            int new_seed_customer = -1;
            int attempts = 0;
            while (attempts < 100 && selected_set.size() < sol.instance.numCustomers) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_set.find(potential_seed) == selected_set.end()) {
                    new_seed_customer = potential_seed;
                    break;
                }
                attempts++;
            }
            
            if (new_seed_customer != -1) {
                selected_set.insert(new_seed_customer);
                selected_list.push_back(new_seed_customer);
                candidates_for_expansion.push_back(new_seed_customer);
            } else {
                break; 
            }
        }

        std::uniform_int_distribution<> dist(0, candidates_for_expansion.size() - 1);
        int current_customer_idx = dist(gen);
        int current_customer = candidates_for_expansion[current_customer_idx];

        bool neighbor_found = false;
        for (int neighbor : sol.instance.adj[current_customer]) {
            if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && 
                selected_set.find(neighbor) == selected_set.end()) {
                
                selected_set.insert(neighbor);
                selected_list.push_back(neighbor);
                candidates_for_expansion.push_back(neighbor);
                neighbor_found = true;
                break;
            }
        }

        if (!neighbor_found) {
            candidates_for_expansion[current_customer_idx] = candidates_for_expansion.back();
            candidates_for_expansion.pop_back();
        }
    }

    return selected_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    float demand_weight = 0.7; 
    float distance_weight = 0.3;

    for (int customer_id : customers) {
        float demand = static_cast<float>(instance.demand[customer_id]);
        float distance_to_depot = instance.distanceMatrix[0][customer_id];
        
        float score = (demand * demand_weight) + (distance_to_depot * distance_weight);
        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    int num_swaps = static_cast<int>(customers.size() * getRandomFraction(0.05, 0.15));
    if (num_swaps < 1 && customers.size() > 1) {
        num_swaps = 1;
    }
    
    std::uniform_int_distribution<> dist_idx(0, customers.size() - 1);

    for (int i = 0; i < num_swaps; ++i) {
        int idx1 = dist_idx(gen);
        int idx2 = dist_idx(gen);
        if (idx1 != idx2) {
            std::swap(customer_scores[idx1], customer_scores[idx2]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}