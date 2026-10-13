#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <chrono>
#include <limits>
#include <numeric>
#include <algorithm>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    if (sol.instance.numCustomers == 0) {
        return {};
    }

    const float MIN_REMOVE_PERCENTAGE = 0.02f;
    const float MAX_REMOVE_PERCENTAGE = 0.06f;
    const int MIN_REMOVE_ABSOLUTE = 5;
    const int MAX_REMOVE_ABSOLUTE = 50;

    const int MAX_OVERALL_EXPANSION_ATTEMPTS = 300;
    const int MIN_NEIGHBORS_TO_CHECK_PER_ATTEMPT = 5;
    const int MAX_NEIGHBORS_TO_CHECK_PER_ATTEMPT = 20;
    const float PROB_NEIGHBOR_SELECTION_BASE = 0.75f;
    const float PROB_NEIGHBOR_SELECTION_VARIANCE = 0.20f;
    const int NEW_SEED_SEARCH_LIMIT = 50; 

    const size_t num_customers = sol.instance.numCustomers;
    size_t min_remove_calc = std::max(static_cast<size_t>(MIN_REMOVE_ABSOLUTE), static_cast<size_t>(num_customers * MIN_REMOVE_PERCENTAGE));
    size_t max_remove_calc = std::min(static_cast<size_t>(MAX_REMOVE_ABSOLUTE), static_cast<size_t>(num_customers * MAX_REMOVE_PERCENTAGE));
    
    if (max_remove_calc < min_remove_calc) { 
        max_remove_calc = min_remove_calc; 
    }

    size_t num_customers_to_remove = getRandomNumber(static_cast<int>(min_remove_calc), static_cast<int>(max_remove_calc));
    num_customers_to_remove = std::min(num_customers_to_remove, num_customers);

    if (num_customers_to_remove == 0) {
        return {};
    }

    std::vector<char> is_selected(num_customers + 1, 0);
    std::vector<int> selected_customers_list;
    selected_customers_list.reserve(num_customers_to_remove);

    std::vector<int> candidate_expansion_customers;
    candidate_expansion_customers.reserve(num_customers_to_remove);

    int initial_seed_customer = getRandomNumber(1, static_cast<int>(num_customers));
    
    is_selected[initial_seed_customer] = 1;
    selected_customers_list.push_back(initial_seed_customer);
    candidate_expansion_customers.push_back(initial_seed_customer);

    int expansion_attempts = 0;

    while (selected_customers_list.size() < num_customers_to_remove && expansion_attempts < MAX_OVERALL_EXPANSION_ATTEMPTS) {
        if (candidate_expansion_customers.empty()) { 
            int new_seed = -1;
            int start_idx = getRandomNumber(1, static_cast<int>(num_customers));
            for (int i = 0; i < NEW_SEED_SEARCH_LIMIT; ++i) { 
                int potential_seed = 1 + (start_idx + i - 1) % num_customers; 
                if (!is_selected[potential_seed]) {
                    new_seed = potential_seed;
                    break;
                }
            }
            
            if (new_seed != -1) {
                is_selected[new_seed] = 1;
                selected_customers_list.push_back(new_seed);
                candidate_expansion_customers.push_back(new_seed);
            } else { 
                if (selected_customers_list.empty()) return {}; 
                break; 
            }
        }
        
        int expand_from_customer = candidate_expansion_customers[getRandomNumber(0, static_cast<int>(candidate_expansion_customers.size()) - 1)];

        const auto& neighbors = sol.instance.adj[expand_from_customer];
        
        int num_neighbors_to_consider = getRandomNumber(MIN_NEIGHBORS_TO_CHECK_PER_ATTEMPT, MAX_NEIGHBORS_TO_CHECK_PER_ATTEMPT);
        num_neighbors_to_consider = std::min(num_neighbors_to_consider, static_cast<int>(neighbors.size()));

        for (int i = 0; i < num_neighbors_to_consider; ++i) {
            int neighbor_id = neighbors[i];

            if (neighbor_id == 0 || is_selected[neighbor_id]) {
                continue;
            }

            const float prob_threshold = PROB_NEIGHBOR_SELECTION_BASE - (getRandomFractionFast() * PROB_NEIGHBOR_SELECTION_VARIANCE);
            
            if (getRandomFractionFast() < prob_threshold) { 
                is_selected[neighbor_id] = 1;
                selected_customers_list.push_back(neighbor_id);
                candidate_expansion_customers.push_back(neighbor_id);
                if (selected_customers_list.size() == num_customers_to_remove) {
                    break;
                }
            }
        }
        
        expansion_attempts++;
    }

    return selected_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float PROB_STRATEGY_DEPOT_SORT = 0.65f;
    const float PROB_STRATEGY_PIVOT_SORT = 0.85f; 
    const float PROB_STRATEGY_COMPOSITE_SORT = 0.95f; 

    const float STOCHASTIC_AMPLITUDE_FACTOR_DEPOT = 0.20f;
    const float STOCHASTIC_AMPLITUDE_MIN_DEPOT = 10.0f;
    const float PROB_ADD_DEMAND_EFFECT_DEPOT_SORT = 0.30f;
    const float DEMAND_FACTOR_MIN_DEPOT_SORT = 0.01f;
    const float DEMAND_FACTOR_MAX_DEPOT_SORT = 0.04f;
    const float PROB_SORT_ASCENDING_DEPOT = 0.30f;

    const float PIVOT_STOCHASTIC_FACTOR = 0.08f;
    const float PROB_SORT_ASCENDING_PIVOT = 0.50f;

    const float COMPOSITE_DIST_WEIGHT = 0.5f;
    const float COMPOSITE_DEMAND_WEIGHT = 0.2f;
    const float COMPOSITE_DEGREE_WEIGHT = 0.05f;
    const float COMPOSITE_STOCHASTIC_FACTOR = 0.10f;
    const float PROB_SORT_ASCENDING_COMPOSITE = 0.50f;

    const float PROB_SORT_DESCENDING_DEMAND = 0.50f;

    const float choice = getRandomFractionFast();

    if (choice < PROB_STRATEGY_DEPOT_SORT) { 
        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size());

        float max_dist_in_set = 0.0f;
        for (int customer_id : customers) {
            const float dist = static_cast<float>(instance.distanceMatrix[0][customer_id]);
            if (dist > max_dist_in_set) {
                max_dist_in_set = dist;
            }
        }
        const float stochastic_amplitude = (max_dist_in_set > 0.0f) ? (max_dist_in_set * STOCHASTIC_AMPLITUDE_FACTOR_DEPOT) : STOCHASTIC_AMPLITUDE_MIN_DEPOT;

        for (int customer_id : customers) {
            float score = static_cast<float>(instance.distanceMatrix[0][customer_id]);
            
            score += (getRandomFractionFast() - 0.5f) * stochastic_amplitude; 

            if (getRandomFractionFast() < PROB_ADD_DEMAND_EFFECT_DEPOT_SORT) { 
                score += static_cast<float>(instance.demand[customer_id]) * 
                         (DEMAND_FACTOR_MIN_DEPOT_SORT + getRandomFractionFast() * 
                         (DEMAND_FACTOR_MAX_DEPOT_SORT - DEMAND_FACTOR_MIN_DEPOT_SORT)); 
            }
            
            customer_scores.push_back({score, customer_id});
        }

        const bool sort_ascending = getRandomFractionFast() < PROB_SORT_ASCENDING_DEPOT;
        std::sort(customer_scores.begin(), customer_scores.end(), [&](const auto& a, const auto& b) {
            return sort_ascending ? (a.first < b.first) : (a.first > b.first);
        });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }
    } 
    else if (choice < PROB_STRATEGY_PIVOT_SORT) {
        if (customers.size() <= 1) { 
            return;
        }

        const int pivot_customer_idx = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
        const int pivot_customer_id = customers[pivot_customer_idx];

        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size());

        for (int customer_id : customers) {
            const float dist_from_pivot = static_cast<float>(instance.distanceMatrix[pivot_customer_id][customer_id]);
            const float score = dist_from_pivot + (getRandomFractionFast() - 0.5f) * PIVOT_STOCHASTIC_FACTOR * dist_from_pivot; 
            
            customer_scores.push_back({score, customer_id});
        }

        const bool sort_ascending = getRandomFractionFast() < PROB_SORT_ASCENDING_PIVOT;
        std::sort(customer_scores.begin(), customer_scores.end(), [&](const auto& a, const auto& b) {
            return sort_ascending ? (a.first < b.first) : (a.first > b.first);
        });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }
    }
    else if (choice < PROB_STRATEGY_COMPOSITE_SORT) { 
        if (customers.size() <= 1) {
            return;
        }

        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size());

        float max_combined_base_score = 0.0f;
        for (int customer_id : customers) {
            float base_score_val = static_cast<float>(instance.distanceMatrix[0][customer_id]) * COMPOSITE_DIST_WEIGHT +
                                   static_cast<float>(instance.demand[customer_id]) * COMPOSITE_DEMAND_WEIGHT;
            if (customer_id > 0 && customer_id < instance.adj.size()) {
                base_score_val += static_cast<float>(instance.adj[customer_id].size()) * COMPOSITE_DEGREE_WEIGHT;
            }
            if (base_score_val > max_combined_base_score) max_combined_base_score = base_score_val;
        }

        const float stochastic_amplitude_composite = (max_combined_base_score > 0.0f) ? (max_combined_base_score * COMPOSITE_STOCHASTIC_FACTOR) : STOCHASTIC_AMPLITUDE_MIN_DEPOT;

        for (int customer_id : customers) {
            float score = static_cast<float>(instance.distanceMatrix[0][customer_id]) * COMPOSITE_DIST_WEIGHT +
                          static_cast<float>(instance.demand[customer_id]) * COMPOSITE_DEMAND_WEIGHT;
            if (customer_id > 0 && customer_id < instance.adj.size()) {
                score += static_cast<float>(instance.adj[customer_id].size()) * COMPOSITE_DEGREE_WEIGHT;
            }
            
            score += (getRandomFractionFast() - 0.5f) * stochastic_amplitude_composite;

            customer_scores.push_back({score, customer_id});
        }

        const bool sort_ascending = getRandomFractionFast() < PROB_SORT_ASCENDING_COMPOSITE;
        std::sort(customer_scores.begin(), customer_scores.end(), [&](const auto& a, const auto& b) {
            return sort_ascending ? (a.first < b.first) : (a.first > b.first);
        });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }
    }
    else { 
        const bool sortDescending = getRandomFractionFast() < PROB_SORT_DESCENDING_DEMAND;
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return sortDescending ? (instance.demand[a] > instance.demand[b]) : (instance.demand[a] < instance.demand[b]);
        });
    }
}