#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <utility>
#include <limits>
#include "Utils.h"

static thread_local std::mt19937 gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    constexpr int MIN_CUSTOMERS_TO_REMOVE = 7;
    constexpr int MAX_CUSTOMERS_TO_REMOVE = 19; 
    constexpr float PROB_TOUR_NEIGHBOR_SELECT = 0.67f; 
    constexpr int NEIGHBORHOOD_EXPLORATION_LIMIT_ADJ = 10;
    constexpr int NUM_LOCAL_SEARCH_ATTEMPTS = 5;
    constexpr int PROBES_PER_TOUR = 5;
    constexpr int INNER_ATTEMPTS_ADJ = 5;
    constexpr int MAX_RANDOM_FIND_ATTEMPTS = 100;
    constexpr float BASE_NEIGHBOR_SELECT_PROB = 0.75f;
    constexpr float PRIZE_DEMAND_ACCEPT_BOOST = 0.237f;
    constexpr float PROB_INITIAL_SERVED_SEED_FROM_TOUR = 0.6f;

    std::vector<int> selected_customers;
    std::vector<bool> is_customer_selected(sol.instance.numCustomers + 1, false); 
    
    std::vector<int> customers_to_expand_from_pool;

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int num_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    if (num_to_remove == 0) {
        return {};
    }
    
    int initial_seed = -1;
    if (!sol.tours.empty() && getRandomFractionFast() < PROB_INITIAL_SERVED_SEED_FROM_TOUR) {
        std::vector<int> served_tours_indices;
        for (size_t i = 0; i < sol.tours.size(); ++i) {
            if (sol.tours[i].customers.size() > 1) {
                served_tours_indices.push_back(static_cast<int>(i));
            }
        }
        if (!served_tours_indices.empty()) {
            int random_tour_idx = served_tours_indices[getRandomNumber(0, static_cast<int>(served_tours_indices.size()) - 1)];
            const Tour& tour = sol.tours[random_tour_idx];
            
            if (!tour.customers.empty()) {
                for (int attempts = 0; attempts < PROBES_PER_TOUR; ++attempts) {
                    int customer_in_tour = tour.customers[getRandomNumber(0, static_cast<int>(tour.customers.size()) - 1)];
                    if (customer_in_tour > 0 && customer_in_tour <= sol.instance.numCustomers) {
                        initial_seed = customer_in_tour;
                        break;
                    }
                }
            }
        }
    }

    if (initial_seed == -1 || initial_seed == 0 || initial_seed > sol.instance.numCustomers) {
        initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    }

    selected_customers.push_back(initial_seed);
    is_customer_selected[initial_seed] = true;
    customers_to_expand_from_pool.push_back(initial_seed);

    while (selected_customers.size() < static_cast<size_t>(num_to_remove)) {
        int next_customer_candidate = -1;
        bool candidate_found_in_current_iteration = false;

        if (!customers_to_expand_from_pool.empty()) {
            for (int attempt = 0; attempt < NUM_LOCAL_SEARCH_ATTEMPTS; ++attempt) {
                int pivot_seed_idx = getRandomNumber(0, static_cast<int>(customers_to_expand_from_pool.size()) - 1);
                int pivot_seed = customers_to_expand_from_pool[pivot_seed_idx];
                
                if (sol.customerToTourMap[pivot_seed] != -1 && 
                    sol.customerToTourMap[pivot_seed] < static_cast<int>(sol.tours.size()) &&
                    getRandomFractionFast() < PROB_TOUR_NEIGHBOR_SELECT) 
                {
                    const Tour& tour = sol.tours[sol.customerToTourMap[pivot_seed]];
                    if (tour.customers.size() > 1) { 
                        for (int probe_idx = 0; probe_idx < PROBES_PER_TOUR; ++probe_idx) {
                            int customer_in_tour = tour.customers[getRandomNumber(0, static_cast<int>(tour.customers.size()) - 1)];
                            if (customer_in_tour > 0 && customer_in_tour <= sol.instance.numCustomers && !is_customer_selected[customer_in_tour]) {
                                float p_d_ratio = (sol.instance.demand[customer_in_tour] > 0) ? 
                                    static_cast<float>(sol.instance.prizes[customer_in_tour]) / sol.instance.demand[customer_in_tour] : 
                                    static_cast<float>(sol.instance.prizes[customer_in_tour]);
                                float current_prob = BASE_NEIGHBOR_SELECT_PROB + p_d_ratio * PRIZE_DEMAND_ACCEPT_BOOST; 
                                current_prob = std::min(1.0f, current_prob);
                                if (getRandomFractionFast() < current_prob) {
                                    next_customer_candidate = customer_in_tour;
                                    candidate_found_in_current_iteration = true;
                                    break;
                                }
                            }
                        }
                    }
                }

                if (candidate_found_in_current_iteration) {
                    break;
                }

                if (pivot_seed > 0 && pivot_seed <= sol.instance.numCustomers) {
                    const std::vector<int>& adj_list = sol.instance.adj[pivot_seed];
                    if (!adj_list.empty()) {
                        int num_neighbors_to_explore = std::min(static_cast<int>(adj_list.size()), NEIGHBORHOOD_EXPLORATION_LIMIT_ADJ);
                        if (num_neighbors_to_explore > 0) {
                            for (int inner_attempts = 0; inner_attempts < INNER_ATTEMPTS_ADJ; ++inner_attempts) {
                                int neighbor = adj_list[getRandomNumber(0, num_neighbors_to_explore - 1)];
                                if (neighbor > 0 && neighbor <= sol.instance.numCustomers && !is_customer_selected[neighbor]) {
                                    float p_d_ratio = (sol.instance.demand[neighbor] > 0) ? 
                                        static_cast<float>(sol.instance.prizes[neighbor]) / sol.instance.demand[neighbor] : 
                                        static_cast<float>(sol.instance.prizes[neighbor]);
                                    float current_prob = BASE_NEIGHBOR_SELECT_PROB + p_d_ratio * PRIZE_DEMAND_ACCEPT_BOOST; 
                                    current_prob = std::min(1.0f, current_prob);
                                    if (getRandomFractionFast() < current_prob) {
                                        next_customer_candidate = neighbor;
                                        candidate_found_in_current_iteration = true;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }

                if (candidate_found_in_current_iteration) {
                    break;
                }
            }
        }

        if (!candidate_found_in_current_iteration) {
            for (int i = 0; i < MAX_RANDOM_FIND_ATTEMPTS; ++i) {
                int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                if (!is_customer_selected[rand_cust]) {
                    next_customer_candidate = rand_cust;
                    candidate_found_in_current_iteration = true;
                    break;
                }
            }
            if (!candidate_found_in_current_iteration) { 
                break;
            }
        }
        
        selected_customers.push_back(next_customer_candidate);
        is_customer_selected[next_customer_candidate] = true;
        customers_to_expand_from_pool.push_back(next_customer_candidate); // Corrected from push_customer_back
    }

    return selected_customers;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    constexpr float PROB_RANDOM_SORT = 0.168f; 
    constexpr float PROB_REVERSE_SORT = 0.15f; 
    constexpr int NUM_PERTURB_SWAPS = 3; 

    constexpr float PRIZE_DEMAND_RATIO_WEIGHT = 2.54f; 
    constexpr float DEPOT_DIST_WEIGHT = -0.0154f; 
    constexpr float DEPOT_DIST_NOISE_MAGNITUDE = 0.1f; 
    constexpr float COMMON_NEIGHBOR_WEIGHT = 6.2f; 
    constexpr int K_ADJ_FOR_SCORE = 10; 
    constexpr float DEMAND_PENALTY_WEIGHT_SORT = 0.0077f; 
    constexpr float ABSOLUTE_PRIZE_WEIGHT_SORT = 0.0051f; 
    constexpr float ABSOLUTE_DEMAND_WEIGHT_SORT = -0.003f; 
    constexpr float STOCHASTIC_SCORE_NOISE_MAGNITUDE = 0.073f; 
    constexpr float SCORE_MULTIPLIER_NOISE = 0.02f; 
    constexpr float PIVOT_PROXIMITY_WEIGHT = 0.954f; 

    constexpr float PROB_PATH_SORT_STRATEGY = 0.17f; 
    constexpr int PATH_SORT_ADJ_SEARCH_LIMIT = 9; 
    constexpr float PATH_SORT_ADJ_CHECK_PROB = 0.75f; 
    constexpr int SORT_PIVOT_SAMPLING_SIZE = 5; 
    constexpr float PIVOT_DEPOT_DIST_PENALTY = 0.0055f;

    if (customers.empty()) {
        return;
    }

    if (getRandomFractionFast() < PROB_RANDOM_SORT) {
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    if (getRandomFractionFast() < PROB_PATH_SORT_STRATEGY && customers.size() > 1) {
        std::vector<int> sorted_customers;
        std::vector<bool> remaining_customers_flag(instance.numCustomers + 1, false);

        for (int customer_id : customers) {
            if (customer_id > 0 && customer_id <= instance.numCustomers) {
                remaining_customers_flag[customer_id] = true;
            }
        }

        int current_customer = customers[getRandomNumber(0, static_cast<int>(customers.size()) - 1)];
        
        sorted_customers.reserve(customers.size());
        sorted_customers.push_back(current_customer);
        remaining_customers_flag[current_customer] = false;

        int customers_remaining_count = static_cast<int>(customers.size()) - 1;

        while (customers_remaining_count > 0) {
            int best_next_customer = -1;
            float min_dist = std::numeric_limits<float>::max();

            bool found_in_adj = false;
            if (current_customer > 0 && current_customer <= instance.numCustomers && getRandomFractionFast() < PATH_SORT_ADJ_CHECK_PROB) { 
                const auto& adj_list_current = instance.adj[current_customer];
                int search_limit = std::min(static_cast<int>(adj_list_current.size()), PATH_SORT_ADJ_SEARCH_LIMIT); 
                for (int i = 0; i < search_limit; ++i) { 
                    int neighbor_node_id = adj_list_current[i];
                    if (neighbor_node_id > 0 && neighbor_node_id <= instance.numCustomers && remaining_customers_flag[neighbor_node_id]) {
                        best_next_customer = neighbor_node_id;
                        found_in_adj = true;
                        break;
                    }
                }
            }

            if (!found_in_adj) {
                for (int customer_id_orig : customers) {
                    if (customer_id_orig > 0 && customer_id_orig <= instance.numCustomers && remaining_customers_flag[customer_id_orig]) {
                        if (current_customer > 0 && current_customer <= instance.numCustomers) {
                            float dist = instance.distanceMatrix[current_customer][customer_id_orig];
                            if (dist < min_dist) {
                                min_dist = dist;
                                best_next_customer = customer_id_orig;
                            }
                        }
                    }
                }
            }
            
            if (best_next_customer != -1) {
                sorted_customers.push_back(best_next_customer);
                remaining_customers_flag[best_next_customer] = false;
                current_customer = best_next_customer;
                customers_remaining_count--;
            } else {
                for (int customer_id_orig : customers) {
                    if (customer_id_orig > 0 && customer_id_orig <= instance.numCustomers && remaining_customers_flag[customer_id_orig]) {
                        sorted_customers.push_back(customer_id_orig);
                        remaining_customers_flag[customer_id_orig] = false;
                        customers_remaining_count--;
                    }
                }
                break; 
            }
        }
        customers = sorted_customers;

    } else { 
        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size());

        std::vector<bool> is_in_removed_set_fast(instance.numCustomers + 1, false);
        for (int customer_id : customers) {
            if (customer_id > 0 && customer_id <= instance.numCustomers) {
                is_in_removed_set_fast[customer_id] = true;
            }
        }

        int pivot_customer = -1;
        float best_pivot_score = -std::numeric_limits<float>::infinity(); 

        if (!customers.empty()) {
            int effective_sampling_size = std::min(SORT_PIVOT_SAMPLING_SIZE, static_cast<int>(customers.size()));
            for (int i = 0; i < effective_sampling_size; ++i) {
                int sample_idx = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
                int current_sample = customers[sample_idx];
                float current_score_for_pivot = (instance.demand[current_sample] > 0) ? 
                                      (static_cast<float>(instance.prizes[current_sample]) / instance.demand[current_sample]) : 
                                      static_cast<float>(instance.prizes[current_sample]); 
                if (current_sample > 0 && current_sample <= instance.numCustomers) {
                    current_score_for_pivot -= instance.distanceMatrix[0][current_sample] * PIVOT_DEPOT_DIST_PENALTY;
                }

                if (current_score_for_pivot > best_pivot_score) {
                    best_pivot_score = current_score_for_pivot;
                    pivot_customer = current_sample;
                }
            }
            if (pivot_customer == -1 && !customers.empty()) {
                 pivot_customer = customers[getRandomNumber(0, static_cast<int>(customers.size()) - 1)];
            }
        } else {
            return;
        }

        for (int customer_id : customers) {
            float score = 0.0f;
            
            score += (instance.prizes[customer_id] / std::max(1.0f, (float)instance.demand[customer_id])) * PRIZE_DEMAND_RATIO_WEIGHT;
            
            if (customer_id > 0 && customer_id <= instance.numCustomers) {
                score += instance.distanceMatrix[0][customer_id] * DEPOT_DIST_WEIGHT * (1.0f + (getRandomFractionFast() * DEPOT_DIST_NOISE_MAGNITUDE - DEPOT_DIST_NOISE_MAGNITUDE / 2.0f));
            }
            
            int common_neighbors_in_removed_set = 0;
            if (customer_id > 0 && customer_id <= instance.numCustomers) {
                const auto& adj_list_for_customer = instance.adj[customer_id];
                for (int i = 0; i < std::min(static_cast<int>(adj_list_for_customer.size()), K_ADJ_FOR_SCORE); ++i) { 
                    int neighbor_id = adj_list_for_customer[i];
                    if (neighbor_id > 0 && neighbor_id <= instance.numCustomers && is_in_removed_set_fast[neighbor_id]) { 
                        common_neighbors_in_removed_set++;
                    }
                }
            }
            score += static_cast<float>(common_neighbors_in_removed_set) * COMMON_NEIGHBOR_WEIGHT;

            if (pivot_customer != -1) {
                if (customer_id != pivot_customer) {
                    if (customer_id > 0 && customer_id <= instance.numCustomers && pivot_customer > 0 && pivot_customer <= instance.numCustomers) {
                       score += (1.0f / (1.0f + instance.distanceMatrix[customer_id][pivot_customer])) * PIVOT_PROXIMITY_WEIGHT;
                    }
                } else {
                   score += PIVOT_PROXIMITY_WEIGHT;
                }
            }

            score -= instance.demand[customer_id] * DEMAND_PENALTY_WEIGHT_SORT;
            score += static_cast<float>(instance.prizes[customer_id]) * ABSOLUTE_PRIZE_WEIGHT_SORT;
            score += static_cast<float>(instance.demand[customer_id]) * ABSOLUTE_DEMAND_WEIGHT_SORT;
            
            score *= (1.0f + (getRandomFractionFast() * 2.0f - 1.0f) * SCORE_MULTIPLIER_NOISE);
            score += (getRandomFractionFast() * 2.0f - 1.0f) * STOCHASTIC_SCORE_NOISE_MAGNITUDE;
            
            customer_scores.push_back({score, customer_id});
        }

        std::sort(customer_scores.begin(), customer_scores.end(),
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                      return a.first > b.first;
                  });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }
    }

    if (getRandomFractionFast() < PROB_REVERSE_SORT) {
        std::reverse(customers.begin(), customers.end());
    }

    for (int k = 0; k < NUM_PERTURB_SWAPS; ++k) {
        if (customers.size() > 1) {
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 2);
            std::swap(customers[idx1], customers[idx1 + 1]);
        } else {
            break;
        }
    }
}