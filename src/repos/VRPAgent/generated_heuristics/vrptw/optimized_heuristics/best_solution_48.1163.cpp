#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <utility>
#include <cmath>
#include <numeric>

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 10;
    const int MAX_CUSTOMERS_TO_REMOVE = 15;
    const int MAX_ATTEMPTS_TO_FIND_NEIGHBOR = 18;
    const double TOUR_NEIGHBOR_PROB = 0.45;
    const double GEO_NEIGHBOR_PROB = 0.35;
    const int MAX_ADJACENCY_CANDIDATES = 18;
    const double STOCHASTIC_POWER_FOR_GEO_NEIGHBORS = 2.0;
    const double PROB_RANDOM_JUMP_DURING_GROWTH = 0.15;
    const int MIN_SELECTED_FOR_RANDOM_JUMP = 3;
    const int MAX_RANDOM_FALLBACK_ATTEMPTS = 300;

    std::vector<int> selected_list;
    std::vector<bool> is_customer_selected(sol.instance.numCustomers + 1, false);

    if (sol.instance.numCustomers == 0) return {};

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    if (numCustomersToRemove <= 0) return {};

    selected_list.reserve(numCustomersToRemove);

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_list.push_back(initial_seed);
    is_customer_selected[initial_seed] = true;

    std::vector<int> expansion_candidates;
    expansion_candidates.push_back(initial_seed);

    while (selected_list.size() < static_cast<size_t>(numCustomersToRemove)) {
        int customer_to_add = -1;
        bool found_connected_candidate_in_attempt = false;

        for (int attempt = 0; attempt < MAX_ATTEMPTS_TO_FIND_NEIGHBOR; ++attempt) {
            if (expansion_candidates.empty()) break;

            int base_customer_idx = expansion_candidates[getRandomNumber(0, static_cast<int>(expansion_candidates.size()) - 1)];

            if (getRandomFraction() < TOUR_NEIGHBOR_PROB) {
                int tour_id = sol.customerToTourMap[base_customer_idx];
                if (tour_id != -1 && tour_id < static_cast<int>(sol.tours.size())) {
                    const Tour& tour = sol.tours[tour_id];
                    if (!tour.customers.empty()) {
                        int pos = -1;
                        for (size_t i = 0; i < tour.customers.size(); ++i) {
                            if (tour.customers[i] == base_customer_idx) {
                                pos = static_cast<int>(i);
                                break;
                            }
                        }

                        if (pos != -1) {
                            std::vector<int> potential_tour_neighbors;
                            if (tour.customers.size() > 1) {
                                int prev_c_idx = (pos - 1 + tour.customers.size()) % tour.customers.size();
                                int prev_c = tour.customers[prev_c_idx];
                                if (prev_c != 0 && !is_customer_selected[prev_c]) {
                                    potential_tour_neighbors.push_back(prev_c);
                                }
                                int next_c_idx = (pos + 1) % tour.customers.size();
                                int next_c = tour.customers[next_c_idx];
                                if (next_c != 0 && !is_customer_selected[next_c]) {
                                    potential_tour_neighbors.push_back(next_c);
                                }
                            }
                            if (!potential_tour_neighbors.empty()) {
                                customer_to_add = potential_tour_neighbors[getRandomNumber(0, static_cast<int>(potential_tour_neighbors.size()) - 1)];
                                found_connected_candidate_in_attempt = true;
                                break;
                            }
                        }
                    }
                }
            }

            if (!found_connected_candidate_in_attempt && getRandomFraction() < GEO_NEIGHBOR_PROB) {
                const auto& neighbors = sol.instance.adj[base_customer_idx];
                if (!neighbors.empty()) {
                    std::vector<int> geo_candidates;
                    for (int i = 0; i < std::min(static_cast<int>(neighbors.size()), MAX_ADJACENCY_CANDIDATES); ++i) {
                        if (neighbors[i] != 0 && !is_customer_selected[neighbors[i]]) {
                            geo_candidates.push_back(neighbors[i]);
                        }
                    }

                    if (!geo_candidates.empty()) {
                        double rand_val_bias = getRandomFraction();
                        int selection_idx = static_cast<int>(std::floor(std::pow(rand_val_bias, STOCHASTIC_POWER_FOR_GEO_NEIGHBORS) * geo_candidates.size()));
                        selection_idx = std::min(selection_idx, static_cast<int>(geo_candidates.size()) - 1);
                        selection_idx = std::max(selection_idx, 0);

                        customer_to_add = geo_candidates[selection_idx];
                        found_connected_candidate_in_attempt = true;
                        break;
                    }
                }
            }
        }

        if (!found_connected_candidate_in_attempt) {
            bool performed_random_jump = false;
            if (selected_list.size() >= MIN_SELECTED_FOR_RANDOM_JUMP && getRandomFraction() < PROB_RANDOM_JUMP_DURING_GROWTH) {
                int random_jump_customer_candidate = -1;
                for (int i = 0; i < MAX_RANDOM_FALLBACK_ATTEMPTS; ++i) {
                    int rand_id = getRandomNumber(1, sol.instance.numCustomers);
                    if (!is_customer_selected[rand_id]) {
                        random_jump_customer_candidate = rand_id;
                        break;
                    }
                }
                if (random_jump_customer_candidate != -1) {
                    customer_to_add = random_jump_customer_candidate;
                    performed_random_jump = true;
                }
            }
            
            if (!performed_random_jump) {
                int random_fallback_attempts = 0;
                do {
                    customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
                    random_fallback_attempts++;
                    if (random_fallback_attempts > MAX_RANDOM_FALLBACK_ATTEMPTS) {
                        customer_to_add = -1;
                        break;
                    }
                } while (customer_to_add != -1 && is_customer_selected[customer_to_add]);
            }
        }

        if (customer_to_add != -1 && !is_customer_selected[customer_to_add]) {
            selected_list.push_back(customer_to_add);
            is_customer_selected[customer_to_add] = true;
            expansion_candidates.push_back(customer_to_add);
        } else {
            break;
        }
    }
    return selected_list;
}

thread_local bool s_instance_metrics_calculated_sort = false;
thread_local float s_max_dist_from_depot_sort = 0.0f;
thread_local float s_min_dist_from_depot_sort = 1e9f;
thread_local float s_max_tw_end_sort = 0.0f;
thread_local float s_min_tw_end_sort = 1e9f;
thread_local float s_max_start_tw_sort = 0.0f;
thread_local float s_min_start_tw_sort = 1e9f;
thread_local float s_max_demand_sort = 0.0f;
thread_local float s_min_demand_sort = 1e9f;
thread_local float s_max_service_time_sort = 0.0f;
thread_local float s_min_service_time_sort = 1e9f;
thread_local float s_max_tw_width_sort = 0.0f;
thread_local float s_min_tw_width_sort = 1e9f;
thread_local int s_cached_num_customers_sort = 0;

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const int NUM_SORTING_STRATEGIES = 10;
    const float REVERSE_SORT_PROBABILITY = 0.25f;
    const int MAX_RANDOM_SWAPS = 2;
    const float TIE_BREAK_RANDOM_FACTOR = 0.0001f;
    const float EPSILON_DIVISION_SAFEGUARD = 1e-6f;

    if (!s_instance_metrics_calculated_sort || s_cached_num_customers_sort != instance.numCustomers) {
        s_max_dist_from_depot_sort = 0.0f; s_min_dist_from_depot_sort = 1e9f;
        s_max_tw_end_sort = 0.0f; s_min_tw_end_sort = 1e9f;
        s_max_start_tw_sort = 0.0f; s_min_start_tw_sort = 1e9f;
        s_max_demand_sort = 0.0f; s_min_demand_sort = 1e9f;
        s_max_service_time_sort = 0.0f; s_min_service_time_sort = 1e9f;
        s_max_tw_width_sort = 0.0f; s_min_tw_width_sort = 1e9f;

        for(int i = 1; i <= instance.numCustomers; ++i) {
            s_max_dist_from_depot_sort = std::max(s_max_dist_from_depot_sort, (float)instance.distanceMatrix[0][i]);
            s_min_dist_from_depot_sort = std::min(s_min_dist_from_depot_sort, (float)instance.distanceMatrix[0][i]);
            s_max_tw_end_sort = std::max(s_max_tw_end_sort, (float)instance.endTW[i]);
            s_min_tw_end_sort = std::min(s_min_tw_end_sort, (float)instance.endTW[i]);
            s_max_start_tw_sort = std::max(s_max_start_tw_sort, (float)instance.startTW[i]);
            s_min_start_tw_sort = std::min(s_min_start_tw_sort, (float)instance.startTW[i]);
            s_max_demand_sort = std::max(s_max_demand_sort, (float)instance.demand[i]);
            s_min_demand_sort = std::min(s_min_demand_sort, (float)instance.demand[i]);
            s_max_service_time_sort = std::max(s_max_service_time_sort, (float)instance.serviceTime[i]);
            s_min_service_time_sort = std::min(s_min_service_time_sort, (float)instance.serviceTime[i]);
            s_max_tw_width_sort = std::max(s_max_tw_width_sort, (float)instance.TW_Width[i]);
            s_min_tw_width_sort = std::min(s_min_tw_width_sort, (float)instance.TW_Width[i]);
        }
        
        if (s_max_dist_from_depot_sort - s_min_dist_from_depot_sort < EPSILON_DIVISION_SAFEGUARD) s_max_dist_from_depot_sort = s_min_dist_from_depot_sort + 1.0f;
        if (s_max_tw_end_sort - s_min_tw_end_sort < EPSILON_DIVISION_SAFEGUARD) s_max_tw_end_sort = s_min_tw_end_sort + 1.0f;
        if (s_max_start_tw_sort - s_min_start_tw_sort < EPSILON_DIVISION_SAFEGUARD) s_max_start_tw_sort = s_min_start_tw_sort + 1.0f;
        if (s_max_demand_sort - s_min_demand_sort < EPSILON_DIVISION_SAFEGUARD) s_max_demand_sort = s_min_demand_sort + 1.0f;
        if (s_max_service_time_sort - s_min_service_time_sort < EPSILON_DIVISION_SAFEGUARD) s_max_service_time_sort = s_min_service_time_sort + 1.0f;
        if (s_max_tw_width_sort - s_min_tw_width_sort < EPSILON_DIVISION_SAFEGUARD) s_max_tw_width_sort = s_min_tw_width_sort + 1.0f;

        s_instance_metrics_calculated_sort = true;
        s_cached_num_customers_sort = instance.numCustomers;
    }

    int strategy = getRandomNumber(0, NUM_SORTING_STRATEGIES - 1);

    if (strategy == 0) {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> sort_values;
    sort_values.reserve(customers.size());

    float w_startTW_rand = 0.0f, w_twWidth_rand = 0.0f, w_demand_rand = 0.0f, w_serviceTime_rand = 0.0f, w_dist_rand = 0.0f;
    float w_polarity_startTW = 0.0f, w_polarity_twWidth = 0.0f;
    float s_w_demand_s9_rand = 0.0f, s_w_twWidth_s9_rand = 0.0f;

    if (strategy == 7) {
        const float RANDOM_WEIGHT_SCALE_FACTOR = 5.0f;
        w_startTW_rand = getRandomFraction() * RANDOM_WEIGHT_SCALE_FACTOR;
        w_twWidth_rand = getRandomFraction() * RANDOM_WEIGHT_SCALE_FACTOR;
        w_demand_rand = getRandomFraction() * RANDOM_WEIGHT_SCALE_FACTOR;
        w_serviceTime_rand = getRandomFraction() * RANDOM_WEIGHT_SCALE_FACTOR;
        w_dist_rand = getRandomFraction() * RANDOM_WEIGHT_SCALE_FACTOR;
        w_polarity_startTW = getRandomFraction();
        w_polarity_twWidth = getRandomFraction();
    } else if (strategy == 9) {
        s_w_demand_s9_rand = getRandomFraction();
        s_w_twWidth_s9_rand = getRandomFraction();
    }

    for (int customer_id : customers) {
        float score = 0.0f;

        switch (strategy) {
            case 1:
                score = (float)instance.TW_Width[customer_id];
                break;
            case 2:
                score = (float)instance.startTW[customer_id];
                break;
            case 3:
                score = - (float)instance.demand[customer_id];
                break;
            case 4:
                score = - instance.distanceMatrix[0][customer_id];
                break;
            case 5:
                score = (float)instance.startTW[customer_id] + 0.5f * (float)instance.TW_Width[customer_id];
                break;
            case 6:
                score = - (float)instance.serviceTime[customer_id];
                break;
            case 7: {
                float normalized_startTW = (static_cast<float>(instance.startTW[customer_id]) - s_min_start_tw_sort) / (s_max_start_tw_sort - s_min_start_tw_sort);
                float normalized_tw_width = (static_cast<float>(instance.TW_Width[customer_id]) - s_min_tw_width_sort) / (s_max_tw_width_sort - s_min_tw_width_sort);
                float normalized_demand = (static_cast<float>(instance.demand[customer_id]) - s_min_demand_sort) / (s_max_demand_sort - s_min_demand_sort);
                float normalized_service_time = (static_cast<float>(instance.serviceTime[customer_id]) - s_min_service_time_sort) / (s_max_service_time_sort - s_min_service_time_sort);
                float normalized_dist_from_depot = (static_cast<float>(instance.distanceMatrix[0][customer_id]) - s_min_dist_from_depot_sort) / (s_max_dist_from_depot_sort - s_min_dist_from_depot_sort);

                float weighted_startTW = (w_polarity_startTW < 0.5f) ? (1.0f - normalized_startTW) : normalized_startTW;
                float weighted_tw_width = (w_polarity_twWidth < 0.5f) ? (1.0f - normalized_tw_width) : normalized_tw_width;

                float current_score = 0.0f;
                current_score += weighted_startTW * w_startTW_rand;
                current_score += weighted_tw_width * w_twWidth_rand;
                current_score += normalized_demand * w_demand_rand;
                current_score += normalized_service_time * w_serviceTime_rand;
                current_score += normalized_dist_from_depot * w_dist_rand;

                score = -current_score;
                break;
            }
            case 8: {
                float earliest_arrival_proxy = instance.distanceMatrix[0][customer_id];
                float latest_arrival_time = (float)instance.endTW[customer_id] - (float)instance.serviceTime[customer_id];
                score = -(latest_arrival_time - earliest_arrival_proxy);
                break;
            }
            case 9: {
                float service_demand_density = (float)instance.demand[customer_id] / ((float)instance.serviceTime[customer_id] + EPSILON_DIVISION_SAFEGUARD);
                float tw_tightness_score = (instance.TW_Width[customer_id] > 0) ? (10.0f / (instance.TW_Width[customer_id] + EPSILON_DIVISION_SAFEGUARD)) : 100.0f;

                float current_score = (service_demand_density * (0.5f + 0.5f * s_w_demand_s9_rand)) + (tw_tightness_score * (0.5f + 0.5f * s_w_twWidth_s9_rand));
                score = -current_score;
                break;
            }
            default:
                score = (float)customer_id;
                break;
        }

        score += getRandomFraction() * TIE_BREAK_RANDOM_FACTOR;
        sort_values.push_back({score, customer_id});
    }

    std::sort(sort_values.begin(), sort_values.end());

    if (getRandomFraction() < REVERSE_SORT_PROBABILITY) {
        std::reverse(sort_values.begin(), sort_values.end());
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_values[i].second;
    }

    int num_swaps = getRandomNumber(0, MAX_RANDOM_SWAPS);
    for (int k = 0; k < num_swaps; ++k) {
        if (customers.size() < 2) {
            break;
        }
        int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
        int idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
        if (idx1 != idx2) {
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}