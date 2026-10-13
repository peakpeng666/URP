#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include <cmath>
#include <limits>
#include "Utils.h"

const int DEPOT_ID = 0;

const int MIN_NUM_TO_REMOVE = 8;
const int MAX_NUM_TO_REMOVE = 22;
const float PROB_START_UNSERVED_CUSTOMER = 0.38f;
const int MIN_ADJ_NEIGHBORS_TO_CHECK = 4;
const int RAND_ADJ_NEIGHBORS_ADD = 5;
const float PROB_ADD_NEIGHBOR_BASE = 0.70f;
const float PROB_ADD_NEIGHBOR_RAND_ADD = 0.15f;
const float PROB_ADD_SAME_TOUR_CUSTOMER_BASE = 0.50f;
const float PROB_ADD_SAME_TOUR_CUSTOMER_RAND_ADD = 0.10f;
const float PROB_TOUR_SEGMENT_REMOVAL = 0.28f;
const int MIN_TOUR_SEGMENT_PCT = 25;
const int MAX_TOUR_SEGMENT_PCT = 75;
const int MAX_STAGNATION_ATTEMPTS = 5;
const int MAX_STAGNATION_SMART_ATTEMPTS = 7;
const float PROB_ADD_RANDOM_ON_STAGNATION = 0.7f;
const int MAX_ATTEMPTS_FIND_UNIQUE_RANDOM = 100;
const float PROB_EXPAND_RECENTLY_ADDED = 0.30f;
const int NUM_RECENT_TO_EXPAND_FROM = 5;
const int MAX_TOUR_CUSTOMERS_TO_SAMPLE = 15;

const float NOISE_SCALE = 0.12f;
const int MIN_POST_SORT_SWAPS = 2;
const int MAX_POST_SORT_SWAPS = 5;

const float P_DYNAMIC_COMPOSITE = 0.45f;
const float P_PRIZE_ONLY = 0.15f;
const float P_NN_AMONG_REMOVED = 0.20f;
const float P_DENSITY_REMOVED = 0.10f;
const float P_NN_PROBABILISTIC = 0.05f;
const float P_PRIZE_DIV_DIST_DEPOT = 0.03f;
const float P_NORMALIZED_MIXED = 0.02f;

const float MIN_COEFF_PRIZE = 0.8f;
const float MAX_COEFF_PRIZE = 1.2f;
const float MIN_COEFF_DIST = 0.02f;
const float MAX_COEFF_DIST = 0.05f;
const float MIN_COEFF_DEMAND = 0.01f;
const float MAX_COEFF_DEMAND = 0.04f;
const float MIN_COEFF_CONNECTIVITY = 0.005f;
const float MAX_COEFF_CONNECTIVITY = 0.02f;
const float ZERO_DEMAND_PRIZE_MULTIPLIER = 2.0f;
const float ZERO_DEMAND_PRIZE_BONUS_FACTOR = 0.1f;

const int MAX_NEIGHBORS_FOR_DENSITY = 10;

const int NN_PROB_CANDIDATES_BASE = 4;
const int NN_PROB_CANDIDATES_RANGE = 2;
const float NN_PROB_TOP_CANDIDATE = 0.45f;
const float NN_PROB_SECOND_CANDIDATE = 0.35f;

const float NORM_PRIZE_WEIGHT = 0.5f;
const float NORM_DIST_TO_DEPOT_WEIGHT = 0.3f;
const float NORM_DEGREE_WEIGHT = 0.2f;


std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<char> is_selected_flag(sol.instance.numCustomers + 1, 0);
    std::vector<int> selected_list;
    selected_list.reserve(MAX_NUM_TO_REMOVE);

    int num_to_remove = getRandomNumber(MIN_NUM_TO_REMOVE, MAX_NUM_TO_REMOVE);
    num_to_remove = std::min(num_to_remove, sol.instance.numCustomers);

    if (num_to_remove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }
    
    if (getRandomFractionFast() < PROB_TOUR_SEGMENT_REMOVAL && !sol.tours.empty()) {
        std::vector<int> active_tours_indices;
        for (size_t i = 0; i < sol.tours.size(); ++i) {
            if (sol.tours[i].customers.size() > 1) { 
                active_tours_indices.push_back(i);
            }
        }

        if (!active_tours_indices.empty()) {
            int random_tour_idx = active_tours_indices[getRandomNumber(0, active_tours_indices.size() - 1)];
            const Tour& tour = sol.tours[random_tour_idx];

            if (!tour.customers.empty()) {
                int min_segment_size_calc = std::max(1, (int)(num_to_remove * MIN_TOUR_SEGMENT_PCT / 100.0f));
                int max_segment_size_calc = (int)(num_to_remove * MAX_TOUR_SEGMENT_PCT / 100.0f);
                
                max_segment_size_calc = std::min((int)tour.customers.size(), max_segment_size_calc);
                max_segment_size_calc = std::max(min_segment_size_calc, max_segment_size_calc);
                
                int desired_segment_size = 0;
                if (min_segment_size_calc <= max_segment_size_calc) {
                    desired_segment_size = getRandomNumber(min_segment_size_calc, max_segment_size_calc);
                }
                
                if (desired_segment_size > 0) {
                    int tour_start_pos = getRandomNumber(0, tour.customers.size() - 1);

                    for (int i = 0; i < desired_segment_size; ++i) {
                        if (selected_list.size() >= (size_t)num_to_remove) break;
                        int customer_idx_in_tour = (tour_start_pos + i) % tour.customers.size();
                        int customer_id = tour.customers[customer_idx_in_tour];
                        if (customer_id != DEPOT_ID && is_selected_flag[customer_id] == 0) {
                            is_selected_flag[customer_id] = 1;
                            selected_list.push_back(customer_id);
                        }
                    }
                }
            }
        }
    }

    if (selected_list.empty()) {
        int initial_seed_customer_id = -1;
        std::vector<int> unserved_customers_candidates;
        if (getRandomFractionFast() < PROB_START_UNSERVED_CUSTOMER) {
            for (int c = 1; c <= sol.instance.numCustomers; ++c) {
                if (sol.customerToTourMap[c] == -1) {
                    unserved_customers_candidates.push_back(c);
                }
            }
        }
        
        if (!unserved_customers_candidates.empty()) {
            initial_seed_customer_id = unserved_customers_candidates[getRandomNumber(0, unserved_customers_candidates.size() - 1)];
        } else {
            initial_seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
        }
        
        if (initial_seed_customer_id != -1 && is_selected_flag[initial_seed_customer_id] == 0) {
            is_selected_flag[initial_seed_customer_id] = 1;
            selected_list.push_back(initial_seed_customer_id);
        } else if (selected_list.empty()) { 
            int new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            while (is_selected_flag[new_random_customer] == 1 && attempts < MAX_ATTEMPTS_FIND_UNIQUE_RANDOM) { 
                new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (is_selected_flag[new_random_customer] == 0) {
                is_selected_flag[new_random_customer] = 1;
                selected_list.push_back(new_random_customer);
            }
        }
    }
    
    int stagnation_count = 0;
    while (selected_list.size() < (size_t)num_to_remove) {
        if (selected_list.empty()) {
            break;
        }

        int expand_from_customer_idx;
        if (getRandomFractionFast() < PROB_EXPAND_RECENTLY_ADDED && selected_list.size() > NUM_RECENT_TO_EXPAND_FROM) {
            expand_from_customer_idx = getRandomNumber(selected_list.size() - NUM_RECENT_TO_EXPAND_FROM, selected_list.size() - 1);
        } else {
            expand_from_customer_idx = getRandomNumber(0, selected_list.size() - 1);
        }
        int expand_from_customer_id = selected_list[expand_from_customer_idx];

        bool added_customer_in_iteration = false;
        
        int num_adj_neighbors_to_check = std::min((int)sol.instance.adj[expand_from_customer_id].size(), MIN_ADJ_NEIGHBORS_TO_CHECK + getRandomNumber(0, RAND_ADJ_NEIGHBORS_ADD));
        for (int i = 0; i < num_adj_neighbors_to_check; ++i) {
            if (selected_list.size() == (size_t)num_to_remove) break;
            int neighbor_node_id = sol.instance.adj[expand_from_customer_id][i];
            
            if (neighbor_node_id == DEPOT_ID) continue;
            
            if (is_selected_flag[neighbor_node_id] == 0) {
                float prob_add_neighbor = PROB_ADD_NEIGHBOR_BASE + (getRandomFractionFast() * PROB_ADD_NEIGHBOR_RAND_ADD);
                if (getRandomFractionFast() < prob_add_neighbor) {
                    is_selected_flag[neighbor_node_id] = 1;
                    selected_list.push_back(neighbor_node_id);
                    added_customer_in_iteration = true;
                }
            }
        }
        if (selected_list.size() == (size_t)num_to_remove) break;

        if (sol.customerToTourMap[expand_from_customer_id] != -1) {
            int tour_idx = sol.customerToTourMap[expand_from_customer_id];
            if (tour_idx >= 0 && tour_idx < (int)sol.tours.size()) {
                std::vector<int> tour_customers_to_consider;
                tour_customers_to_consider.reserve(std::min((int)sol.tours[tour_idx].customers.size(), MAX_TOUR_CUSTOMERS_TO_SAMPLE));

                if (sol.tours[tour_idx].customers.size() <= MAX_TOUR_CUSTOMERS_TO_SAMPLE) {
                    tour_customers_to_consider = sol.tours[tour_idx].customers;
                } else {
                    std::vector<int> tour_customers_copy = sol.tours[tour_idx].customers;
                    std::shuffle(tour_customers_copy.begin(), tour_customers_copy.end(), std::default_random_engine(getRandomNumber(0, 1000000)));
                    for(int i = 0; i < MAX_TOUR_CUSTOMERS_TO_SAMPLE; ++i) {
                        tour_customers_to_consider.push_back(tour_customers_copy[i]);
                    }
                }

                for (int tour_customer_id : tour_customers_to_consider) {
                    if (selected_list.size() == (size_t)num_to_remove) break;
                    if (tour_customer_id == expand_from_customer_id || tour_customer_id == DEPOT_ID) continue;
                    if (is_selected_flag[tour_customer_id] == 0) {
                        float prob_add_same_tour = PROB_ADD_SAME_TOUR_CUSTOMER_BASE + (getRandomFractionFast() * PROB_ADD_SAME_TOUR_CUSTOMER_RAND_ADD);
                        if (getRandomFractionFast() < prob_add_same_tour) {
                            is_selected_flag[tour_customer_id] = 1;
                            selected_list.push_back(tour_customer_id);
                            added_customer_in_iteration = true;
                        }
                    }
                }
            }
        }
        if (selected_list.size() == (size_t)num_to_remove) break;

        if (!added_customer_in_iteration) {
            stagnation_count++;
            if (stagnation_count >= MAX_STAGNATION_ATTEMPTS) {
                bool smart_added = false;
                for (int i = 0; i < MAX_STAGNATION_SMART_ATTEMPTS; ++i) {
                    if (selected_list.empty()) break; 
                    int pivot_customer_id = selected_list[getRandomNumber(0, static_cast<int>(selected_list.size()) - 1)];
                    if (pivot_customer_id > 0 && pivot_customer_id <= sol.instance.numCustomers && !sol.instance.adj[pivot_customer_id].empty()) {
                        int random_neighbor_idx = getRandomNumber(0, static_cast<int>(sol.instance.adj[pivot_customer_id].size()) - 1);
                        int neighbor_node_id = sol.instance.adj[pivot_customer_id][random_neighbor_idx];
                        if (neighbor_node_id != DEPOT_ID && is_selected_flag[neighbor_node_id] == 0) {
                            is_selected_flag[neighbor_node_id] = 1;
                            selected_list.push_back(neighbor_node_id);
                            smart_added = true;
                            break;
                        }
                    }
                }

                if (!smart_added && getRandomFractionFast() < PROB_ADD_RANDOM_ON_STAGNATION) {
                    int new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
                    int attempts = 0;
                    while (is_selected_flag[new_random_customer] == 1 && attempts < MAX_ATTEMPTS_FIND_UNIQUE_RANDOM) { 
                        new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
                        attempts++;
                    }
                    if (is_selected_flag[new_random_customer] == 0) {
                        is_selected_flag[new_random_customer] = 1;
                        selected_list.push_back(new_random_customer);
                        added_customer_in_iteration = true; 
                    }
                }
                stagnation_count = 0;
            }
        } else {
            stagnation_count = 0;
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

    float strategy_rand_val = getRandomFractionFast();
    bool apply_score_based_sort = true;

    float current_prob_sum = 0.0f;

    if (strategy_rand_val < (current_prob_sum += P_DYNAMIC_COMPOSITE)) {
        float current_coeff_prize = MIN_COEFF_PRIZE + (getRandomFractionFast() * (MAX_COEFF_PRIZE - MIN_COEFF_PRIZE));
        float current_coeff_dist = MIN_COEFF_DIST + (getRandomFractionFast() * (MAX_COEFF_DIST - MIN_COEFF_DIST));
        float current_coeff_demand = MIN_COEFF_DEMAND + (getRandomFractionFast() * (MAX_COEFF_DEMAND - MIN_COEFF_DEMAND));
        float current_coeff_connectivity = MIN_COEFF_CONNECTIVITY + (getRandomFractionFast() * (MAX_COEFF_CONNECTIVITY - MIN_COEFF_CONNECTIVITY));

        for (int customer_id : customers) {
            float prize_term = instance.prizes[customer_id];
            if (instance.demand[customer_id] > 0) {
                prize_term /= instance.demand[customer_id];
            } else {
                prize_term *= ZERO_DEMAND_PRIZE_MULTIPLIER;
                prize_term += instance.prizes[customer_id] * ZERO_DEMAND_PRIZE_BONUS_FACTOR;
            }

            float score = prize_term * current_coeff_prize;
            score -= (instance.distanceMatrix[DEPOT_ID][customer_id] * current_coeff_dist);
            score -= (instance.demand[customer_id] * current_coeff_demand);
            score += (instance.adj[customer_id].size() * current_coeff_connectivity);
            customer_scores.push_back({score, customer_id});
        }
    } else if (strategy_rand_val < (current_prob_sum += P_PRIZE_ONLY)) {
        for (int customer_id : customers) {
            float score = instance.prizes[customer_id];
            customer_scores.push_back({score, customer_id});
        }
    } else if (strategy_rand_val < (current_prob_sum += P_NN_AMONG_REMOVED)) {
        std::vector<int> ordered_result;
        ordered_result.reserve(customers.size());
        
        std::vector<char> visited_map(instance.numCustomers + 1, 0);
        int num_remaining = customers.size();

        int current_idx_in_original_list = getRandomNumber(0, customers.size() - 1);
        int current_node = customers[current_idx_in_original_list];
        ordered_result.push_back(current_node);
        visited_map[current_node] = 1;
        num_remaining--;

        while (num_remaining > 0) {
            float min_dist_val = std::numeric_limits<float>::max();
            int best_next_node = -1;

            for (int customer_id : customers) {
                if (visited_map[customer_id] == 0) {
                    float dist_val = instance.distanceMatrix[current_node][customer_id];
                    if (dist_val < min_dist_val) {
                        min_dist_val = dist_val;
                        best_next_node = customer_id;
                    }
                }
            }
           
            if (best_next_node != -1) {
                current_node = best_next_node;
                ordered_result.push_back(current_node);
                visited_map[current_node] = 1;
                num_remaining--;
            } else { 
                for (int customer_id : customers) {
                    if (visited_map[customer_id] == 0) {
                        ordered_result.push_back(customer_id);
                        visited_map[customer_id] = 1;
                        num_remaining--;
                    }
                }
                break;
            }
        }
        
        customers = ordered_result;
        apply_score_based_sort = false;
        return; 
    } else if (strategy_rand_val < (current_prob_sum += P_DENSITY_REMOVED)) {
        std::vector<char> is_removed_flag(instance.numCustomers + 1, 0);
        for (int customer_id : customers) {
            is_removed_flag[customer_id] = 1;
        }

        for (int customer_id : customers) {
            float density_score = 0.0f;
            int neighbors_considered = 0;
            
            for (int neighbor : instance.adj[customer_id]) {
                if (neighbors_considered >= MAX_NEIGHBORS_FOR_DENSITY) {
                    break;
                }
                if (neighbor == DEPOT_ID) continue; 
                if (is_removed_flag[neighbor] == 1) {
                    density_score += 1.0f; 
                }
                neighbors_considered++;
            }
            customer_scores.push_back({density_score, customer_id});
        }
    } else if (strategy_rand_val < (current_prob_sum += P_NN_PROBABILISTIC)) {
        std::vector<int> sorted_customers;
        sorted_customers.reserve(customers.size());
        std::vector<bool> customers_in_pool(instance.numCustomers + 1, false);
        for(int c_id : customers) {
            customers_in_pool[c_id] = true;
        }
        int pool_size = customers.size();

        int current_customer_id = customers[getRandomNumber(0, static_cast<int>(customers.size()) - 1)];
        sorted_customers.push_back(current_customer_id);
        customers_in_pool[current_customer_id] = false;
        pool_size--;

        while (pool_size > 0) {
            std::vector<std::pair<float, int>> closest_candidates;
            closest_candidates.reserve(pool_size);

            for (int c_id : customers) {
                if (customers_in_pool[c_id]) {
                    closest_candidates.emplace_back(static_cast<float>(instance.distanceMatrix[current_customer_id][c_id]), c_id);
                }
            }

            int next_customer_id = -1;
            if (closest_candidates.empty()) { 
                for(int c_id : customers) { 
                    if(customers_in_pool[c_id]) {
                        next_customer_id = c_id;
                        break;
                    }
                }
            } else {
                int num_to_sort_limit = std::min(static_cast<int>(closest_candidates.size()), NN_PROB_CANDIDATES_BASE + getRandomNumber(0, NN_PROB_CANDIDATES_RANGE));
                
                if (num_to_sort_limit > 0) {
                     std::partial_sort(closest_candidates.begin(), closest_candidates.begin() + num_to_sort_limit, closest_candidates.end());
                } else {
                    next_customer_id = closest_candidates[0].second;
                }

                if (next_customer_id == -1) { 
                    float r = getRandomFractionFast();
                    if (num_to_sort_limit >= 1 && r < NN_PROB_TOP_CANDIDATE) {
                        next_customer_id = closest_candidates[0].second;
                    } else if (num_to_sort_limit >= 2 && r < (NN_PROB_TOP_CANDIDATE + NN_PROB_SECOND_CANDIDATE)) {
                        next_customer_id = closest_candidates[1].second;
                    } else {
                        next_customer_id = closest_candidates[getRandomNumber(0, num_to_sort_limit - 1)].second;
                    }
                }
            }
            
            if (next_customer_id != -1) {
                sorted_customers.push_back(next_customer_id);
                customers_in_pool[next_customer_id] = false;
                current_customer_id = next_customer_id;
                pool_size--;
            } else { 
                break;
            }
        }
        customers = sorted_customers;
        apply_score_based_sort = false;
        return;
    } else if (strategy_rand_val < (current_prob_sum += P_PRIZE_DIV_DIST_DEPOT)) {
        for (int customer_id : customers) {
            float score = 0.0f;
            if (instance.distanceMatrix[DEPOT_ID][customer_id] > 0.0f) {
                score = instance.prizes[customer_id] / instance.distanceMatrix[DEPOT_ID][customer_id];
            } else {
                score = instance.prizes[customer_id] * 1000.0f; 
            }
            customer_scores.push_back({score, customer_id});
        }
    } else if (strategy_rand_val < (current_prob_sum += P_NORMALIZED_MIXED)) {
        float max_prize_in_removed = 0.0f;
        float max_dist_to_depot_in_removed = 0.0f;
        float max_degree_in_removed = 0.0f;
        
        for (int customer_id : customers) {
            max_prize_in_removed = std::max(max_prize_in_removed, instance.prizes[customer_id]);
            max_dist_to_depot_in_removed = std::max(max_dist_to_depot_in_removed, instance.distanceMatrix[DEPOT_ID][customer_id]);
            max_degree_in_removed = std::max(max_degree_in_removed, static_cast<float>(instance.adj[customer_id].size()));
        }
        if (max_prize_in_removed < std::numeric_limits<float>::epsilon()) max_prize_in_removed = 1.0f;
        if (max_dist_to_depot_in_removed < std::numeric_limits<float>::epsilon()) max_dist_to_depot_in_removed = 1.0f;
        if (max_degree_in_removed < std::numeric_limits<float>::epsilon()) max_degree_in_removed = 1.0f;

        for (int customer_id : customers) {
            float normalized_prize = instance.prizes[customer_id] / max_prize_in_removed;
            float normalized_inv_dist_to_depot = 1.0f - (instance.distanceMatrix[DEPOT_ID][customer_id] / max_dist_to_depot_in_removed);
            float normalized_degree = static_cast<float>(instance.adj[customer_id].size()) / max_degree_in_removed;
            
            float score = NORM_PRIZE_WEIGHT * normalized_prize
                        + NORM_DIST_TO_DEPOT_WEIGHT * normalized_inv_dist_to_depot
                        + NORM_DEGREE_WEIGHT * normalized_degree;
            customer_scores.push_back({score, customer_id});
        }
    } else { 
        std::shuffle(customers.begin(), customers.end(), std::default_random_engine(getRandomNumber(0, 1000000)));
        apply_score_based_sort = false;
        return; 
    }

    if (!customer_scores.empty() && apply_score_based_sort) {
        for (auto& p : customer_scores) {
            p.first += NOISE_SCALE * (getRandomFractionFast() - 0.5f);
        }

        std::sort(customer_scores.begin(), customer_scores.end(),
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                      return a.first > b.first;
                  });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }

        int num_swaps = getRandomNumber(MIN_POST_SORT_SWAPS, MAX_POST_SORT_SWAPS); 
        for (int i = 0; i < num_swaps; ++i) {
            if (customers.size() < 2) break;
            int idx1 = getRandomNumber(0, customers.size() - 1);
            int idx2 = getRandomNumber(0, customers.size() - 1);
            if (idx1 != idx2) {
                std::swap(customers[idx1], customers[idx2]);
            }
        }
    }
}