#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <utility>
#include <functional>
#include <limits>

const int MIN_CUSTOMERS_TO_REMOVE_LLM = 10;
const int MAX_CUSTOMERS_TO_REMOVE_LLM = 15;

const int MIN_NEIGHBOR_CONSIDERATION_LLM = 5;
const int MAX_NEIGHBOR_CONSIDERATION_LLM = 10;

const float TOUR_NEIGHBOR_ADD_PROB_LLM = 0.35f;
const int MAX_TOUR_NEIGHBORS_TO_ADD_LLM = 3;
const int MAX_SEED_ATTEMPTS_LLM = 20;

const float BASE_NEIGHBOR_PROB_LLM = 0.58f;
const float UNSERVED_BONUS_PROB_LLM = 0.3f;
const float PRIZE_BONUS_FACTOR_LLM = 0.14f;

const float STOCHASTIC_EXPANSION_PROB_LLM = 0.15f;
const int STOCHASTIC_EXPANSION_NEIGHBOR_FACTOR_LLM = 2;

const float SELECT_UNSERVED_SEED_PROB_LLM = 0.18f;
const float RANDOM_SERVED_CUSTOMER_INJECTION_PROB_LLM = 0.09f;
const int MAX_INJECTION_ATTEMPTS_LLM = 10;
const int MAX_UNPRODUCTIVE_ATTEMPTS_LLM = 50;

const float PRIZE_WEIGHT_SORT_LLM = 1.0f;
const float DISTANCE_TO_DEPOT_WEIGHT_LLM = 0.18f;
const float DEMAND_PENALTY_WEIGHT_LLM = 0.05f;
const float NEAREST_NEIGHBOR_DIST_WEIGHT_LLM = 0.04f;
const float NUM_NEIGHBORS_WEIGHT_LLM = 0.01f;
const float PRIZE_TO_DEMAND_RATIO_WEIGHT_LLM = 0.7f;
const float DEMAND_EPSILON_FOR_SORT_LLM = 0.1f;
const float SORT_NOISE_FACTOR_VAL_LLM = 2.0f;

const float ABSOLUTE_PRIZE_ADD_WEIGHT_LLM = 0.012f;
const float SIMPLER_SCORE_PROB_LLM = 0.2f;
const float SIMPLER_PRIZE_WEIGHT_LLM = 0.05f;
const float SIMPLER_DISTANCE_WEIGHT_LLM = 0.01f;

const float ALTERNATIVE_SCORE_STRATEGY_PROB_LLM = 0.1f;
const float ALTERNATIVE_SCORE_STRATEGY_MAGNITUDE_LLM = 9.0f;
const float HIGH_PRIZE_NO_DEMAND_BONUS_LLM = 1000.0f;

const int SORT_SHUFFLE_PROB_PERCENT_LLM = 10;
const float SCORE_MODULATION_PROB_LLM = 0.30f;
const float PRIZE_DEMAND_BOOST_FACTOR_LLM = 2.0f;
const float DISTANCE_PROXIMITY_BOOST_FACTOR_LLM = 2.0f;
const float RANDOM_SCORE_BOOST_FACTOR_LLM = 5.0f;

const float SORT_PRIZE_DEMAND_ADJUST_PROB_LLM = 0.15f;
const float SORT_PRIZE_DEMAND_ADJUST_FACTOR_LLM = 0.03f;
const float PRIZE_DEMAND_DIFF_ADJ_FACTOR_LLM_SORT = 1.0f;
const float DISTANCE_TO_DEPOT_WEIGHT_VARIANCE_LLM = 0.05f;

const float REMOVED_NEIGHBOR_BONUS_WEIGHT_LLM = 0.28f;
const int NEIGHBORS_CONSIDERED_FOR_BONUS_LLM = 5;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selected_customers_list;
    selected_customers_list.reserve(MAX_CUSTOMERS_TO_REMOVE_LLM);
    
    std::vector<bool> is_selected(sol.instance.numCustomers + 1, false);
    std::vector<bool> in_candidate_pool_set(sol.instance.numCustomers + 1, false);
    std::vector<int> candidate_pool;
    candidate_pool.reserve(MAX_CUSTOMERS_TO_REMOVE_LLM * MAX_NEIGHBOR_CONSIDERATION_LLM);

    int num_customers_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE_LLM, MAX_CUSTOMERS_TO_REMOVE_LLM);
    num_customers_to_remove = std::min(num_customers_to_remove, sol.instance.numCustomers);
    if (num_customers_to_remove == 0 || sol.instance.numCustomers == 0) {
        return selected_customers_list;
    }

    float max_prize_val = 0.0f;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.instance.prizes[i] > max_prize_val) {
            max_prize_val = static_cast<float>(sol.instance.prizes[i]);
        }
    }
    if (max_prize_val == 0.0f) max_prize_val = 1.0f;

    auto add_neighbors_to_pool = [&](int customer_id, int consideration_count_param) {
        if (customer_id < 1 || customer_id > sol.instance.numCustomers) {
            return;
        }
        const auto& adj_list = sol.instance.adj[customer_id];
        int num_neighbors_to_consider = std::min((int)adj_list.size(), getRandomNumber(1, consideration_count_param));

        for (int neighbor_idx = 0; neighbor_idx < num_neighbors_to_consider; ++neighbor_idx) {
            int neighbor = adj_list[neighbor_idx];
            if (neighbor == 0 || neighbor > sol.instance.numCustomers || is_selected[neighbor] || in_candidate_pool_set[neighbor]) {
                continue;
            }

            float selection_probability = BASE_NEIGHBOR_PROB_LLM;
            if (sol.customerToTourMap[neighbor] == -1) {
                selection_probability += UNSERVED_BONUS_PROB_LLM;
            }
            selection_probability += (static_cast<float>(sol.instance.prizes[neighbor]) / max_prize_val) * PRIZE_BONUS_FACTOR_LLM;

            if (getRandomFractionFast() < selection_probability) {
                candidate_pool.push_back(neighbor);
                in_candidate_pool_set[neighbor] = true;
            }
        }
    };

    int seed_customer = -1;
    if (getRandomFractionFast() < SELECT_UNSERVED_SEED_PROB_LLM) {
        std::vector<int> unserved_customers;
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (sol.customerToTourMap[i] == -1) {
                unserved_customers.push_back(i);
            }
        }
        if (!unserved_customers.empty()) {
            seed_customer = unserved_customers[getRandomNumber(0, static_cast<int>(unserved_customers.size() - 1))];
        }
    }

    if (seed_customer == -1) {
        int attempts = 0;
        while (attempts < MAX_SEED_ATTEMPTS_LLM && seed_customer == -1) {
            int temp_seed = getRandomNumber(1, sol.instance.numCustomers);
            if (sol.customerToTourMap[temp_seed] != -1) {
                seed_customer = temp_seed;
            }
            attempts++;
        }
    }
    if (seed_customer == -1) {
        seed_customer = getRandomNumber(1, sol.instance.numCustomers);
        if (seed_customer < 1) seed_customer = 1;
        if (seed_customer > sol.instance.numCustomers) seed_customer = sol.instance.numCustomers;
    }
    
    if (seed_customer < 1 || seed_customer > sol.instance.numCustomers || is_selected[seed_customer]) {
        bool found_valid_seed = false;
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (!is_selected[i]) {
                seed_customer = i;
                found_valid_seed = true;
                break;
            }
        }
        if (!found_valid_seed) return selected_customers_list;
    }

    selected_customers_list.push_back(seed_customer);
    is_selected[seed_customer] = true;
    add_neighbors_to_pool(seed_customer, getRandomNumber(MIN_NEIGHBOR_CONSIDERATION_LLM, MAX_NEIGHBOR_CONSIDERATION_LLM));

    int unproductive_attempts = 0;
    while (selected_customers_list.size() < static_cast<size_t>(num_customers_to_remove)) {
        int next_customer_to_add = -1;

        if (getRandomFractionFast() < RANDOM_SERVED_CUSTOMER_INJECTION_PROB_LLM) {
            int attempts = 0;
            while(attempts < MAX_INJECTION_ATTEMPTS_LLM) {
                int temp_c = getRandomNumber(1, sol.instance.numCustomers);
                if (sol.customerToTourMap[temp_c] != -1 && !is_selected[temp_c] && !in_candidate_pool_set[temp_c]) {
                    candidate_pool.push_back(temp_c);
                    in_candidate_pool_set[temp_c] = true;
                    break;
                }
                attempts++;
            }
        }

        if (!candidate_pool.empty()) {
            int random_idx = getRandomNumber(0, static_cast<int>(candidate_pool.size() - 1));
            next_customer_to_add = candidate_pool[random_idx];

            candidate_pool[random_idx] = candidate_pool.back();
            candidate_pool.pop_back();
            in_candidate_pool_set[next_customer_to_add] = false;
        } else {
            unproductive_attempts++;
        }

        if (next_customer_to_add != -1 && !is_selected[next_customer_to_add]) {
            selected_customers_list.push_back(next_customer_to_add);
            is_selected[next_customer_to_add] = true;
            unproductive_attempts = 0;

            add_neighbors_to_pool(next_customer_to_add, getRandomNumber(MIN_NEIGHBOR_CONSIDERATION_LLM, MAX_NEIGHBOR_CONSIDERATION_LLM));

            if (getRandomFractionFast() < TOUR_NEIGHBOR_ADD_PROB_LLM && sol.customerToTourMap[next_customer_to_add] != -1) {
                int tour_idx = sol.customerToTourMap[next_customer_to_add];
                if (tour_idx >= 0 && static_cast<size_t>(tour_idx) < sol.tours.size()) {
                    const auto& tour_customers = sol.tours[tour_idx].customers;
                    std::vector<int> candidates_from_tour;
                    candidates_from_tour.reserve(tour_customers.size());
                    for (int c_in_tour : tour_customers) {
                        if (c_in_tour != 0 && c_in_tour != next_customer_to_add && !is_selected[c_in_tour] && !in_candidate_pool_set[c_in_tour]) {
                            candidates_from_tour.push_back(c_in_tour);
                        }
                    }

                    int added_count = 0;
                    while (added_count < MAX_TOUR_NEIGHBORS_TO_ADD_LLM && !candidates_from_tour.empty()) {
                        int rand_idx = getRandomNumber(0, static_cast<int>(candidates_from_tour.size() - 1));
                        int tour_mate = candidates_from_tour[rand_idx];
                        
                        if (!in_candidate_pool_set[tour_mate]) {
                            candidate_pool.push_back(tour_mate);
                            in_candidate_pool_set[tour_mate] = true;
                            added_count++;
                        }
                        candidates_from_tour[rand_idx] = candidates_from_tour.back();
                        candidates_from_tour.pop_back();
                    }
                }
            }

            if (selected_customers_list.size() > 1 && getRandomFractionFast() < STOCHASTIC_EXPANSION_PROB_LLM) {
                int random_selected_idx = getRandomNumber(0, static_cast<int>(selected_customers_list.size() - 1));
                int pivot_customer_for_expansion = selected_customers_list[random_selected_idx];
                add_neighbors_to_pool(pivot_customer_for_expansion, getRandomNumber(MIN_NEIGHBOR_CONSIDERATION_LLM, MAX_NEIGHBOR_CONSIDERATION_LLM) * STOCHASTIC_EXPANSION_NEIGHBOR_FACTOR_LLM);
            }
        } else if (unproductive_attempts >= MAX_UNPRODUCTIVE_ATTEMPTS_LLM) {
            int new_seed_candidate = -1;
            int attempts = 0;
            while (attempts < MAX_SEED_ATTEMPTS_LLM) {
                int temp_c = getRandomNumber(1, sol.instance.numCustomers);
                if (!is_selected[temp_c]) {
                     if (sol.customerToTourMap[temp_c] != -1) {
                        new_seed_candidate = temp_c;
                        break;
                    } else if (new_seed_candidate == -1) {
                        new_seed_candidate = temp_c;
                    }
                }
                attempts++;
            }
            if (new_seed_candidate != -1) {
                selected_customers_list.push_back(new_seed_candidate);
                is_selected[new_seed_candidate] = true;
                unproductive_attempts = 0;
                add_neighbors_to_pool(new_seed_candidate, getRandomNumber(MIN_NEIGHBOR_CONSIDERATION_LLM, MAX_NEIGHBOR_CONSIDERATION_LLM));
            } else {
                break;
            }
        }
    }
    return selected_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    if (getRandomNumber(0, 99) < SORT_SHUFFLE_PROB_PERCENT_LLM) {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    std::vector<bool> is_removed_customer_flag(instance.numCustomers + 1, false);
    for (int customer_id : customers) {
        if (customer_id >= 1 && customer_id <= instance.numCustomers) {
            is_removed_customer_flag[customer_id] = true;
        }
    }

    float base_dist_to_depot_weight_modulated = DISTANCE_TO_DEPOT_WEIGHT_LLM + (getRandomFractionFast() - 0.5f) * DISTANCE_TO_DEPOT_WEIGHT_VARIANCE_LLM * 2.0f;

    for (int customer_id : customers) {
        float score = 0.0f;
        float prize = 0.0f;
        float demand = 0.0f;
        float distToDepot = 0.0f;

        if (customer_id >= 1 && customer_id <= instance.numCustomers) {
            prize = static_cast<float>(instance.prizes[customer_id]);
            demand = static_cast<float>(instance.demand[customer_id]);
            distToDepot = static_cast<float>(instance.distanceMatrix[customer_id][0]);

            float current_prize_weight = PRIZE_WEIGHT_SORT_LLM;
            float current_prize_to_demand_ratio_weight = PRIZE_TO_DEMAND_RATIO_WEIGHT_LLM;
            float current_distance_to_depot_weight = base_dist_to_depot_weight_modulated;
            float current_demand_penalty_weight = DEMAND_PENALTY_WEIGHT_LLM;
            float current_nearest_neighbor_dist_weight = NEAREST_NEIGHBOR_DIST_WEIGHT_LLM;
            float current_num_neighbors_weight = NUM_NEIGHBORS_WEIGHT_LLM;
            float current_absolute_prize_add_weight = ABSOLUTE_PRIZE_ADD_WEIGHT_LLM;
            
            if (getRandomFractionFast() < SCORE_MODULATION_PROB_LLM) {
                int modulation_choice = getRandomNumber(0, 2);
                if (modulation_choice == 0) {
                    current_prize_weight *= PRIZE_DEMAND_BOOST_FACTOR_LLM;
                    current_prize_to_demand_ratio_weight *= PRIZE_DEMAND_BOOST_FACTOR_LLM;
                } else if (modulation_choice == 1) {
                    current_distance_to_depot_weight *= DISTANCE_PROXIMITY_BOOST_FACTOR_LLM;
                    current_nearest_neighbor_dist_weight *= DISTANCE_PROXIMITY_BOOST_FACTOR_LLM;
                } else {
                    score += getRandomFractionFast() * RANDOM_SCORE_BOOST_FACTOR_LLM;
                }
            }

            score += current_prize_weight * prize;
            score += current_absolute_prize_add_weight * prize;

            score += current_prize_to_demand_ratio_weight * (prize / (demand + DEMAND_EPSILON_FOR_SORT_LLM));

            score -= current_distance_to_depot_weight * distToDepot;

            score -= current_demand_penalty_weight * demand;

            float min_dist_to_neighbor = 0.0f;
            if (!instance.adj[customer_id].empty() && instance.adj[customer_id][0] >= 1 && instance.adj[customer_id][0] <= instance.numCustomers) {
                min_dist_to_neighbor = static_cast<float>(instance.distanceMatrix[customer_id][instance.adj[customer_id][0]]);
            } else {
                min_dist_to_neighbor = distToDepot;
            }
            score -= current_nearest_neighbor_dist_weight * min_dist_to_neighbor;

            score += current_num_neighbors_weight * static_cast<float>(instance.adj[customer_id].size());

            float removed_neighbor_bonus = 0.0f;
            int neighbors_to_check = std::min(static_cast<int>(instance.adj[customer_id].size()), NEIGHBORS_CONSIDERED_FOR_BONUS_LLM);
            for (int i = 0; i < neighbors_to_check; ++i) {
                int neighbor = instance.adj[customer_id][i];
                if (neighbor >= 1 && neighbor <= instance.numCustomers && is_removed_customer_flag[neighbor]) {
                    removed_neighbor_bonus += REMOVED_NEIGHBOR_BONUS_WEIGHT_LLM;
                }
            }
            score += removed_neighbor_bonus;

            if (getRandomFractionFast() < SORT_PRIZE_DEMAND_ADJUST_PROB_LLM) {
                score += (prize - demand) * SORT_PRIZE_DEMAND_ADJUST_FACTOR_LLM;
            }

        } else {
            score = -std::numeric_limits<float>::infinity();
        }

        if (getRandomFractionFast() < SIMPLER_SCORE_PROB_LLM) {
            score += SIMPLER_PRIZE_WEIGHT_LLM * prize;
            score -= SIMPLER_DISTANCE_WEIGHT_LLM * distToDepot;
        }

        if (getRandomFractionFast() < ALTERNATIVE_SCORE_STRATEGY_PROB_LLM) {
            int strategy_choice = getRandomNumber(0, 3);
            float alt_influence = 0.0f;
            switch (strategy_choice) {
                case 0:
                    if (demand > DEMAND_EPSILON_FOR_SORT_LLM) { 
                        alt_influence = prize / demand;
                    } else {
                        alt_influence = prize * HIGH_PRIZE_NO_DEMAND_BONUS_LLM;
                    }
                    break;
                case 1:
                    alt_influence = -distToDepot;
                    break;
                case 2:
                    alt_influence = static_cast<float>(instance.adj[customer_id].size());
                    break;
                case 3:
                     alt_influence = (prize - demand) * PRIZE_DEMAND_DIFF_ADJ_FACTOR_LLM_SORT;
                     break;
            }
            score += alt_influence * (ALTERNATIVE_SCORE_STRATEGY_MAGNITUDE_LLM / 100.0f);
        }
        
        score += (getRandomFractionFast() - 0.5f) * SORT_NOISE_FACTOR_VAL_LLM;

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}