#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <utility>
#include <cmath>
#include "Utils.h"

static thread_local std::mt19937 shuffle_gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 9;
    const int MAX_CUSTOMERS_TO_REMOVE = 15; 
    const float PROB_SEED_FROM_SERVED = 0.7496f;
    const float PROB_SEED_FROM_UNSERVED_IF_NO_SERVED = 0.33f;
    const float PROB_ADD_FROM_TOUR = 0.710f; 
    const float PROB_ADD_FROM_NEIGHBORS = 0.810f; 
    const int MAX_NEIGHBORS_TO_CONSIDER = 38;
    const int MAX_NEW_SEED_ATTEMPTS = 113;
    const int MAX_INITIAL_SEED_ATTEMPTS = 75; 
    const float PROB_EARLY_NEW_SEED_TRIGGER = 0.10f;
    const float THRESHOLD_FOR_EARLY_NEW_SEED = 0.35f;
    const float PROB_RANDOM_NEW_SEED_DURING_EXPANSION = 0.013f;

    int num_customers_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (num_customers_to_remove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    std::vector<char> is_selected_vec(sol.instance.numCustomers + 1, 0);
    std::vector<int> customers_to_return;
    customers_to_return.reserve(static_cast<size_t>(num_customers_to_remove) + 5);
    std::vector<int> customers_to_process;
    customers_to_process.reserve(static_cast<size_t>(num_customers_to_remove) + 5);

    auto add_customer_if_unselected = [&](int customer_id, float probability) {
        if (customer_id > 0 && customer_id <= sol.instance.numCustomers && is_selected_vec[customer_id] == 0) {
            if (getRandomFractionFast() < probability) {
                is_selected_vec[customer_id] = 1;
                customers_to_return.push_back(customer_id);
                customers_to_process.push_back(customer_id);
                return true;
            }
        }
        return false;
    };

    int seed_customer = -1;

    if (sol.instance.numCustomers > 0) {
        bool served_seed_attempted = false;
        if (getRandomFractionFast() < PROB_SEED_FROM_SERVED && !sol.tours.empty()) {
            served_seed_attempted = true;
            for (int attempt = 0; attempt < MAX_INITIAL_SEED_ATTEMPTS; ++attempt) {
                int tour_idx = getRandomNumber(0, static_cast<int>(sol.tours.size()) - 1);
                const Tour& tour = sol.tours[tour_idx];
                if (!tour.customers.empty()) {
                    seed_customer = tour.customers[getRandomNumber(0, static_cast<int>(tour.customers.size()) - 1)];
                    break;
                }
            }
        }
        
        if (seed_customer == -1 && (getRandomFractionFast() < PROB_SEED_FROM_UNSERVED_IF_NO_SERVED || !served_seed_attempted)) {
            for (int attempt = 0; attempt < MAX_INITIAL_SEED_ATTEMPTS; ++attempt) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (sol.customerToTourMap[potential_seed] == -1) { 
                    seed_customer = potential_seed;
                    break;
                }
            }
        }

        if (seed_customer == -1) {
            seed_customer = getRandomNumber(1, sol.instance.numCustomers);
        }
    }

    if (seed_customer == -1) {
        return {}; 
    }

    is_selected_vec[seed_customer] = 1;
    customers_to_return.push_back(seed_customer);
    customers_to_process.push_back(seed_customer);

    if (sol.customerToTourMap[seed_customer] != -1) {
        const Tour& tour = sol.tours[sol.customerToTourMap[seed_customer]];
        for (int cust_in_tour : tour.customers) {
            if (customers_to_return.size() >= static_cast<size_t>(num_customers_to_remove)) break;
            add_customer_if_unselected(cust_in_tour, PROB_ADD_FROM_TOUR);
        }
    }

    int head = 0;

    while (customers_to_return.size() < static_cast<size_t>(num_customers_to_remove)) {
        bool current_path_exhausted = (head >= static_cast<int>(customers_to_process.size()));
        bool force_new_seed_early = (!current_path_exhausted && 
                                    customers_to_return.size() < static_cast<size_t>(num_customers_to_remove * THRESHOLD_FOR_EARLY_NEW_SEED) && 
                                    getRandomFractionFast() < PROB_EARLY_NEW_SEED_TRIGGER);
        bool random_new_seed_during_expansion = getRandomFractionFast() < PROB_RANDOM_NEW_SEED_DURING_EXPANSION;

        if (current_path_exhausted || force_new_seed_early || random_new_seed_during_expansion) {
            int new_seed = -1;
            int new_seed_attempts = 0;
            while (new_seed == -1 && new_seed_attempts < MAX_NEW_SEED_ATTEMPTS) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (is_selected_vec[potential_seed] == 0) {
                    new_seed = potential_seed;
                }
                new_seed_attempts++;
            }

            if (new_seed == -1) {
                break; 
            }
            
            is_selected_vec[new_seed] = 1;
            customers_to_return.push_back(new_seed);
            customers_to_process.push_back(new_seed);

            if (sol.customerToTourMap[new_seed] != -1) {
                const Tour& tour = sol.tours[sol.customerToTourMap[new_seed]];
                for (int cust_in_tour : tour.customers) {
                    if (customers_to_return.size() >= static_cast<size_t>(num_customers_to_remove)) break;
                    add_customer_if_unselected(cust_in_tour, PROB_ADD_FROM_TOUR);
                }
            }
            head = static_cast<int>(customers_to_process.size()) - 1; 
            if (head < 0) head = 0; 
            continue;
        }

        int current_customer = customers_to_process[head];
        head++;

        int neighbors_considered_count = 0;
        for (int neighbor : sol.instance.adj[current_customer]) {
            if (customers_to_return.size() >= static_cast<size_t>(num_customers_to_remove)) break;
            if (neighbors_considered_count++ >= MAX_NEIGHBORS_TO_CONSIDER) break;
            add_customer_if_unselected(neighbor, PROB_ADD_FROM_NEIGHBORS);
        }

        if (sol.customerToTourMap[current_customer] != -1) {
            const Tour& tour = sol.tours[sol.customerToTourMap[current_customer]];
            for (int cust_in_tour : tour.customers) {
                if (cust_in_tour == current_customer || cust_in_tour == 0) continue;
                if (customers_to_return.size() >= static_cast<size_t>(num_customers_to_remove)) break;
                add_customer_if_unselected(cust_in_tour, PROB_ADD_FROM_TOUR);
            }
        }
    }

    if (customers_to_return.size() > static_cast<size_t>(num_customers_to_remove)) {
        customers_to_return.resize(num_customers_to_remove);
    }

    return customers_to_return;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float PROB_FULL_SHUFFLE = 0.1104f;

    const float MIN_PRIZE_WEIGHT = 0.96f;
    const float MAX_PRIZE_WEIGHT = 1.299f;
    const float MIN_DEMAND_WEIGHT = -0.0620f; 
    const float MAX_DEMAND_WEIGHT = -0.0235f;
    const float MIN_DIST_COST_WEIGHT = -0.0327f; 
    const float MAX_DIST_COST_WEIGHT = -0.0185f;
    const float MIN_DEGREE_WEIGHT = 0.0485f;
    const float MAX_DEGREE_WEIGHT = 0.096f;
    const float MIN_PRIZE_TO_DEPOT_RATIO_WEIGHT = 0.170f;
    const float MAX_PRIZE_TO_DEPOT_RATIO_WEIGHT = 0.350f;
    const float MIN_COMPREHENSIVE_EFFICIENCY_WEIGHT = 0.245f; 
    const float MAX_COMPREHENSIVE_EFFICIENCY_WEIGHT = 0.445f;
    const float MIN_PRIZE_DEMAND_RATIO_WEIGHT = 0.078f; 
    const float MAX_PRIZE_DEMAND_RATIO_WEIGHT = 0.1745f;
    
    const float MIN_STOCHASTIC_NOISE_RANGE = 28.0f;
    const float MAX_STOCHASTIC_NOISE_RANGE = 73.0f;

    const float PROB_POST_SORT_SWAPS = 0.190f;
    const int MIN_POST_SORT_SWAPS = 2;
    const int MAX_FIXED_POST_SORT_SWAPS = 4;
    const float HIGH_PRIZE_ZERO_DEMAND_FACTOR = 850.0f;

    if (getRandomFractionFast() < PROB_FULL_SHUFFLE) {
        std::shuffle(customers.begin(), customers.end(), shuffle_gen);
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    float prize_weight = getRandomFraction(MIN_PRIZE_WEIGHT, MAX_PRIZE_WEIGHT);
    float demand_weight = getRandomFraction(MIN_DEMAND_WEIGHT, MAX_DEMAND_WEIGHT);
    float distance_cost_weight = getRandomFraction(MIN_DIST_COST_WEIGHT, MAX_DIST_COST_WEIGHT);
    float degree_weight = getRandomFraction(MIN_DEGREE_WEIGHT, MAX_DEGREE_WEIGHT);
    float prize_to_depot_ratio_weight = getRandomFraction(MIN_PRIZE_TO_DEPOT_RATIO_WEIGHT, MAX_PRIZE_TO_DEPOT_RATIO_WEIGHT);
    float comprehensive_efficiency_weight = getRandomFraction(MIN_COMPREHENSIVE_EFFICIENCY_WEIGHT, MAX_COMPREHENSIVE_EFFICIENCY_WEIGHT);
    float prize_demand_ratio_weight = getRandomFraction(MIN_PRIZE_DEMAND_RATIO_WEIGHT, MAX_PRIZE_DEMAND_RATIO_WEIGHT);
    
    float stochastic_noise_range = getRandomFraction(MIN_STOCHASTIC_NOISE_RANGE, MAX_STOCHASTIC_NOISE_RANGE);

    float vehicle_capacity_f = static_cast<float>(instance.vehicleCapacity);
    if (vehicle_capacity_f == 0) vehicle_capacity_f = 1.0f;
    
    for (int customer_id : customers) {
        float score = 0.0f;

        score += static_cast<float>(instance.prizes[customer_id]) * prize_weight;
        score += (static_cast<float>(instance.demand[customer_id]) / vehicle_capacity_f) * demand_weight; 
        score += (static_cast<float>(instance.distanceMatrix[0][customer_id]) + static_cast<float>(instance.distanceMatrix[customer_id][0])) * distance_cost_weight;
        score += static_cast<float>(instance.adj[customer_id].size()) * degree_weight;

        float effective_distance_to_depot = std::max(1.0f, static_cast<float>(instance.distanceMatrix[0][customer_id]));
        score += (static_cast<float>(instance.prizes[customer_id]) / effective_distance_to_depot) * prize_to_depot_ratio_weight;

        float effective_demand_for_ratio = std::max(1.0f, static_cast<float>(instance.demand[customer_id]));
        float comprehensive_efficiency_denominator = std::max(1.0f, effective_demand_for_ratio + effective_distance_to_depot);
        float comprehensive_efficiency_factor = static_cast<float>(instance.prizes[customer_id]) / comprehensive_efficiency_denominator;
        score += comprehensive_efficiency_factor * comprehensive_efficiency_weight;

        if (instance.demand[customer_id] > 0) {
            score += (static_cast<float>(instance.prizes[customer_id]) / effective_demand_for_ratio) * prize_demand_ratio_weight;
        } else if (instance.prizes[customer_id] > 0) {
             score += HIGH_PRIZE_ZERO_DEMAND_FACTOR * prize_demand_ratio_weight;
        }

        score += (getRandomFractionFast() * stochastic_noise_range) - (stochastic_noise_range / 2.0f);

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.rbegin(), customer_scores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }

    if (!customers.empty() && getRandomFractionFast() < PROB_POST_SORT_SWAPS) {
        int num_swaps = 0;
        int num_swaps_candidate = std::min(static_cast<int>(customers.size() / 3), MAX_FIXED_POST_SORT_SWAPS);

        if (customers.size() < 2) {
            num_swaps = 0;
        } else if (num_swaps_candidate >= MIN_POST_SORT_SWAPS) {
            num_swaps = getRandomNumber(MIN_POST_SORT_SWAPS, num_swaps_candidate);
        } else if (num_swaps_candidate > 0) {
            num_swaps = getRandomNumber(1, num_swaps_candidate);
        }
        
        for (int i = 0; i < num_swaps; ++i) {
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            int idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            if (idx1 != idx2) {
                std::swap(customers[idx1], customers[idx2]);
            }
        }
    }
}