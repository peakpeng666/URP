#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <numeric>
#include <cmath>
#include <array>

static thread_local std::mt19937 generator(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUST_REMOVE = 6;
    const int MAX_CUST_REMOVE = 15;
    const int MAX_STUCK_ITERS = 20;
    const int NEW_SEED_ATTEMPTS = 30;
    const int NEIGHBOR_EXPLORE_LIMIT = 15;
    const float NEIGHBOR_SELECTION_BIAS_POWER = 2.0f;
    const float NEIGHBOR_ACCEPTANCE_PROB = 0.95f;
    const float UNBIASED_NEIGHBOR_SELECTION_PROB = 0.08f;

    std::vector<int> selected_customers;
    selected_customers.reserve(MAX_CUST_REMOVE);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    std::vector<char> is_selected(sol.instance.numCustomers + 1, 0);

    int num_to_remove = getRandomNumber(MIN_CUST_REMOVE, MAX_CUST_REMOVE);
    if (num_to_remove <= 0) {
        return {};
    }

    int initial_seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers.push_back(initial_seed_customer_id);
    is_selected[initial_seed_customer_id] = 1;

    int stuck_counter = 0;
    while (selected_customers.size() < static_cast<size_t>(num_to_remove)) {
        bool customer_added_in_current_major_iteration = false;
        
        if (selected_customers.empty()) {
            break;
        }
        int anchor = selected_customers[getRandomNumber(0, static_cast<int>(selected_customers.size()) - 1)];
        const auto& neighbors = sol.instance.adj[anchor];
        
        std::array<int, NEIGHBOR_EXPLORE_LIMIT> potential_next_customers_arr;
        int current_potential_count = 0;

        int actual_neighbors_to_check = std::min(static_cast<int>(neighbors.size()), NEIGHBOR_EXPLORE_LIMIT);
        for (int i = 0; i < actual_neighbors_to_check; ++i) {
            int neighbor_id = neighbors[i];
            if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers && is_selected[neighbor_id] == 0) {
                if (current_potential_count < NEIGHBOR_EXPLORE_LIMIT) {
                    potential_next_customers_arr[current_potential_count++] = neighbor_id;
                }
            }
        }

        if (current_potential_count > 0) {
            int chosen_idx;
            if (getRandomFraction() < UNBIASED_NEIGHBOR_SELECTION_PROB) {
                chosen_idx = getRandomNumber(0, current_potential_count - 1);
            } else {
                float r = getRandomFraction();
                chosen_idx = static_cast<int>(current_potential_count * std::pow(r, NEIGHBOR_SELECTION_BIAS_POWER));
                chosen_idx = std::min(chosen_idx, current_potential_count - 1);
            }

            int candidate_customer = potential_next_customers_arr[chosen_idx];
            
            if (getRandomFraction() < NEIGHBOR_ACCEPTANCE_PROB) {
                is_selected[candidate_customer] = 1;
                selected_customers.push_back(candidate_customer);
                customer_added_in_current_major_iteration = true;
            }
        }
        
        if (customer_added_in_current_major_iteration) {
            stuck_counter = 0;
        } else {
            stuck_counter++;
            if (stuck_counter >= MAX_STUCK_ITERS) {
                bool added_new_seed = false;
                for (int i = 0; i < NEW_SEED_ATTEMPTS; ++i) {
                    int new_seed_id = getRandomNumber(1, sol.instance.numCustomers);
                    if (is_selected[new_seed_id] == 0) {
                        is_selected[new_seed_id] = 1;
                        selected_customers.push_back(new_seed_id);
                        stuck_counter = 0;
                        added_new_seed = true;
                        break;
                    }
                }
                if (!added_new_seed) {
                    break;
                }
            }
        }
    }
    
    if (selected_customers.size() > static_cast<size_t>(num_to_remove)) {
        selected_customers.resize(num_to_remove);
    }
    return selected_customers;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float K_DEPOT_DIST_PENALTY_FACTOR = 0.0058f;
    const float K_DEMAND_EPSILON = 1.0f;
    const float DEGREE_BONUS_WEIGHT = 0.0045f;
    const float PERTURBATION_ADDITIVE_SCALE = 0.55f;
    const float PERTURBATION_MULT_RANGE = 0.055f;
    const int MAX_POST_SORT_SWAPS = 3;
    const float PURE_PRIZE_PERTURBATION_RANGE = 0.6f;

    const int MAIN_SCORE_PROB_PERCENT = 80;
    const int PURE_PRIZE_PROB_PERCENT = 15;
    const int SHUFFLE_PROB_PERCENT = 5;

    int strategy_choice = getRandomNumber(0, 99);

    if (strategy_choice < MAIN_SCORE_PROB_PERCENT) {
        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size());

        for (int customer_id : customers) {
            float prize = static_cast<float>(instance.prizes[customer_id]);
            float demand = static_cast<float>(instance.demand[customer_id]);
            float dist_to_depot = instance.distanceMatrix[0][customer_id];
            float degree = static_cast<float>(instance.adj[customer_id].size());

            float score = (prize / (demand + K_DEMAND_EPSILON)) - (K_DEPOT_DIST_PENALTY_FACTOR * dist_to_depot);
            score += (DEGREE_BONUS_WEIGHT * degree);
            
            score += (getRandomFraction() - 0.5f) * PERTURBATION_ADDITIVE_SCALE;
            score *= (1.0f + (getRandomFraction() - 0.5f) * PERTURBATION_MULT_RANGE);

            customer_scores.push_back({score, customer_id});
        }

        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });

        int num_swaps = getRandomNumber(0, MAX_POST_SORT_SWAPS);
        for (int k = 0; k < num_swaps; ++k) {
            if (customer_scores.size() < 2) {
                break;
            }
            int idx1 = getRandomNumber(0, static_cast<int>(customer_scores.size()) - 1);
            int idx2 = getRandomNumber(0, static_cast<int>(customer_scores.size()) - 1);
            if (idx1 != idx2) {
                std::swap(customer_scores[idx1], customer_scores[idx2]);
            }
        }

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }
    } else if (strategy_choice < MAIN_SCORE_PROB_PERCENT + PURE_PRIZE_PROB_PERCENT) {
        std::vector<std::pair<float, int>> scored_customers;
        scored_customers.reserve(customers.size());

        for (int customer_id : customers) {
            float score = static_cast<float>(instance.prizes[customer_id]);
            score += (getRandomFraction() - 0.5f) * PURE_PRIZE_PERTURBATION_RANGE;
            scored_customers.push_back({score, customer_id});
        }

        std::sort(scored_customers.begin(), scored_customers.end(),
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                      return a.first > b.first;
                  });
        
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scored_customers[i].second;
        }
    } else {
        std::shuffle(customers.begin(), customers.end(), generator);
    }
}