#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <utility>
#include <numeric>
#include <limits>
#include <cmath>

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 8;
    const int MAX_CUSTOMERS_TO_REMOVE = 18;
    const float GEOGRAPHIC_ADDITION_PROBABILITY = 0.78f;
    const float TOUR_MATE_ADDITION_PROBABILITY = 0.72f;
    const float PREFER_GEOGRAPHIC_PROB = 0.56f;
    
    const int MIN_NEIGHBOR_CANDIDATES_TO_CHECK = 3;
    const int MAX_NEIGHBOR_CANDIDATES_TO_CHECK = 10;
    const int MIN_TOUR_MATE_CANDIDATES_TO_CHECK = 4;
    const int MAX_TOUR_MATE_CANDIDATES_TO_CHECK = 8;

    if (sol.instance.numCustomers == 0) return {};

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    if (numCustomersToRemove == 0) return {};

    std::vector<char> is_selected(sol.instance.numCustomers + 1, 0);
    std::vector<int> selectedCustomersVec;
    selectedCustomersVec.reserve(static_cast<size_t>(numCustomersToRemove));

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    is_selected[initialCustomer] = 1;
    selectedCustomersVec.push_back(initialCustomer);

    while (selectedCustomersVec.size() < static_cast<size_t>(numCustomersToRemove)) {
        int expandFromCustomer = selectedCustomersVec[getRandomNumber(0, static_cast<int>(selectedCustomersVec.size()) - 1)];
        
        bool customerAddedThisRound = false;
        bool currentStrategyIsGeographic = (getRandomFractionFast() < PREFER_GEOGRAPHIC_PROB);
        int neighborsToConsider = getRandomNumber(MIN_NEIGHBOR_CANDIDATES_TO_CHECK, MAX_NEIGHBOR_CANDIDATES_TO_CHECK);
        int tourMatesToConsider = getRandomNumber(MIN_TOUR_MATE_CANDIDATES_TO_CHECK, MAX_TOUR_MATE_CANDIDATES_TO_CHECK);

        for (int i = 0; i < 2; ++i) { 
            if (currentStrategyIsGeographic) {
                int checked_count = 0;
                if (static_cast<size_t>(expandFromCustomer) < sol.instance.adj.size()) {
                    for (int neighborId : sol.instance.adj[expandFromCustomer]) {
                        if (neighborId == 0) continue; 
                        if (is_selected[neighborId] == 0) {
                            if (getRandomFractionFast() < GEOGRAPHIC_ADDITION_PROBABILITY) {
                                is_selected[neighborId] = 1;
                                selectedCustomersVec.push_back(neighborId);
                                customerAddedThisRound = true;
                                if (selectedCustomersVec.size() >= static_cast<size_t>(numCustomersToRemove)) break;
                            }
                        }
                        checked_count++;
                        if (checked_count >= neighborsToConsider) break;
                    }
                }
            } else {
                if (sol.customerToTourMap[expandFromCustomer] != -1) {
                    const Tour& currentTour = sol.tours[sol.customerToTourMap[expandFromCustomer]];
                    int tour_size = static_cast<int>(currentTour.customers.size());
                    if (tour_size > 0) {
                        int start_idx = getRandomNumber(0, tour_size - 1); 
                        int checked_count = 0;
                        for (int k = 0; k < tour_size; ++k) {
                            int tourMate_idx = (start_idx + k) % tour_size; 
                            int tourMate = currentTour.customers[tourMate_idx];

                            if (tourMate == 0 || tourMate == expandFromCustomer) continue;
                            if (is_selected[tourMate] == 0) {
                                if (getRandomFractionFast() < TOUR_MATE_ADDITION_PROBABILITY) {
                                    is_selected[tourMate] = 1;
                                    selectedCustomersVec.push_back(tourMate);
                                    customerAddedThisRound = true;
                                    if (selectedCustomersVec.size() >= static_cast<size_t>(numCustomersToRemove)) break;
                                }
                            }
                            checked_count++;
                            if (checked_count >= tourMatesToConsider) break;
                        }
                    }
                }
            }
            if (selectedCustomersVec.size() >= static_cast<size_t>(numCustomersToRemove)) break;
            currentStrategyIsGeographic = !currentStrategyIsGeographic; 
        }
    }

    while (selectedCustomersVec.size() < static_cast<size_t>(numCustomersToRemove)) {
        int randomNewCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (is_selected[randomNewCustomer] == 0) {
            is_selected[randomNewCustomer] = 1;
            selectedCustomersVec.push_back(randomNewCustomer);
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float DISTANCE_DENOMINATOR_EPSILON = 0.1f;
    const float PRIMARY_NOISE_SCALE = 17.5f; 
    const float SECONDARY_NOISE_FACTOR = 0.07f; 
    const int MAX_CONNECTIVITY_NEIGHBORS_TO_CHECK = 10; 
    const float REVERSE_ORDER_PROBABILITY = 0.18f;
    const float WEIGHT_PRIZE_MINUS_DIST_SCORE = 0.72f; 

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    int strategy_choice_category = getRandomNumber(0, 99); 

    if (strategy_choice_category < 30) { 
        const float WEIGHT_DEMAND_PRIMARY_SCORE = 0.04f;
        for (int customerId : customers) {
            float prize = static_cast<float>(instance.prizes[customerId]);
            float distToDepot = static_cast<float>(instance.distanceMatrix[0][customerId]);
            float demand = static_cast<float>(instance.demand[customerId]);
            float score = (prize / (distToDepot + DISTANCE_DENOMINATOR_EPSILON)) - WEIGHT_DEMAND_PRIMARY_SCORE * demand;
            
            float randomNoise = (getRandomFractionFast() - 0.5f) * PRIMARY_NOISE_SCALE * (std::abs(score) + 1.0f);
            score += randomNoise;
            
            customerScores.push_back({score, customerId});
        }
    } else if (strategy_choice_category < 30 + 25) { 
        std::vector<int> current_customer_ids_to_consider;
        current_customer_ids_to_consider.reserve(customers.size());
        for(int customerId : customers) {
            current_customer_ids_to_consider.push_back(customerId);
        }

        std::vector<int> final_sorted_customers;
        final_sorted_customers.reserve(customers.size());

        if (current_customer_ids_to_consider.empty()) {
            customers.clear(); return;
        }

        int rand_idx_in_consider_list = getRandomNumber(0, static_cast<int>(current_customer_ids_to_consider.size()) - 1);
        int current_customer_id = current_customer_ids_to_consider[rand_idx_in_consider_list];
        
        final_sorted_customers.push_back(current_customer_id);
        
        std::swap(current_customer_ids_to_consider[rand_idx_in_consider_list], current_customer_ids_to_consider.back());
        current_customer_ids_to_consider.pop_back();

        while (!current_customer_ids_to_consider.empty()) {
            int next_customer_candidate_id = -1;
            float min_dist = std::numeric_limits<float>::max();
            int best_idx_in_consider_list = -1;

            for (size_t i = 0; i < current_customer_ids_to_consider.size(); ++i) {
                int candidate_id = current_customer_ids_to_consider[i];
                if (static_cast<size_t>(current_customer_id) < instance.distanceMatrix.size() &&
                    static_cast<size_t>(candidate_id) < instance.distanceMatrix[current_customer_id].size()) {
                    float dist = static_cast<float>(instance.distanceMatrix[current_customer_id][candidate_id]);
                    if (dist < min_dist) {
                        min_dist = dist;
                        next_customer_candidate_id = candidate_id;
                        best_idx_in_consider_list = static_cast<int>(i);
                    }
                }
            }
            
            final_sorted_customers.push_back(next_customer_candidate_id);
            
            std::swap(current_customer_ids_to_consider[best_idx_in_consider_list], current_customer_ids_to_consider.back());
            current_customer_ids_to_consider.pop_back();
            
            current_customer_id = next_customer_candidate_id;
        }
        customers = final_sorted_customers;
        if (getRandomFractionFast() < REVERSE_ORDER_PROBABILITY) {
            std::reverse(customers.begin(), customers.end());
        }
        return; 
    } else if (strategy_choice_category < 30 + 25 + 15) { 
        std::vector<char> is_removed_lookup(instance.numCustomers + 1, 0);
        for(int cust_id : customers) {
            is_removed_lookup[cust_id] = 1;
        }
        
        for (int customerId : customers) {
            float internal_connectivity_score = 0.0f;
            int neighbors_checked_count = 0;
            if (static_cast<size_t>(customerId) < instance.adj.size()) {
                for (int neighbor : instance.adj[customerId]) {
                    if (neighbor == 0) continue;
                    if (is_removed_lookup[neighbor]) { 
                        if (static_cast<size_t>(customerId) < instance.distanceMatrix.size() &&
                            static_cast<size_t>(neighbor) < instance.distanceMatrix[customerId].size()) {
                            internal_connectivity_score += static_cast<float>(instance.prizes[neighbor]) / (static_cast<float>(instance.distanceMatrix[customerId][neighbor]) + DISTANCE_DENOMINATOR_EPSILON);
                        }
                    }
                    neighbors_checked_count++;
                    if (neighbors_checked_count >= MAX_CONNECTIVITY_NEIGHBORS_TO_CHECK) break;
                }
            }
            float score = internal_connectivity_score;
            score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * (score + 1.0f);
            customerScores.push_back({score, customerId});
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6) { 
        for (int customerId : customers) {
            float prize = static_cast<float>(instance.prizes[customerId]);
            float demand = static_cast<float>(instance.demand[customerId]);
            float score = prize / (demand + DISTANCE_DENOMINATOR_EPSILON);
            score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * score;
            customerScores.push_back({score, customerId});
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6 + 6) { 
        for (int customerId : customers) {
            if (static_cast<size_t>(customerId) < instance.distanceMatrix[0].size()) {
                float score = -static_cast<float>(instance.distanceMatrix[0][customerId]);
                score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * (std::abs(score) + 1.0f);
                customerScores.push_back({score, customerId});
            } else {
                customerScores.push_back({-std::numeric_limits<float>::max(), customerId});
            }
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6 + 6 + 5) { 
        for (int customerId : customers) {
            float prize = static_cast<float>(instance.prizes[customerId]);
            float distToDepot = static_cast<float>(instance.distanceMatrix[0][customerId]);
            float demand = static_cast<float>(instance.demand[customerId]);
            float score = prize / (distToDepot + demand + DISTANCE_DENOMINATOR_EPSILON);
            score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * score;
            customerScores.push_back({score, customerId});
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6 + 6 + 5 + 4) { 
        for (int customerId : customers) {
            float centrality_sum_inverse_dist = 0.0f;
            for (int other_customer_id : customers) { 
                if (customerId == other_customer_id) continue;
                if (static_cast<size_t>(customerId) < instance.distanceMatrix.size() &&
                    static_cast<size_t>(other_customer_id) < instance.distanceMatrix[customerId].size()) {
                    centrality_sum_inverse_dist += 1.0f / (static_cast<float>(instance.distanceMatrix[customerId][other_customer_id]) + DISTANCE_DENOMINATOR_EPSILON);
                }
            }
            float score = centrality_sum_inverse_dist;
            score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * (std::abs(score) + 1.0f);
            customerScores.push_back({score, customerId});
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6 + 6 + 5 + 4 + 2) { 
        for (int customerId : customers) {
            if (static_cast<size_t>(customerId) < instance.distanceMatrix[0].size()) {
                float prize = static_cast<float>(instance.prizes[customerId]);
                float distToDepot = static_cast<float>(instance.distanceMatrix[0][customerId]);
                float score = prize - WEIGHT_PRIZE_MINUS_DIST_SCORE * distToDepot;
                score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * (std::abs(score) + 1.0f);
                customerScores.push_back({score, customerId});
            } else {
                customerScores.push_back({-std::numeric_limits<float>::max(), customerId});
            }
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6 + 6 + 5 + 4 + 2 + 2) { 
        std::vector<char> is_removed_lookup(instance.numCustomers + 1, 0);
        for(int cust_id : customers) {
            is_removed_lookup[cust_id] = 1;
        }
        for (int customerId : customers) {
            int num_nearby_removed = 0;
            int neighbors_checked_count = 0;
            if (static_cast<size_t>(customerId) < instance.adj.size()) {
                for (int neighbor : instance.adj[customerId]) {
                    if (neighbor == 0) continue;
                    if (is_removed_lookup[neighbor]) {
                        num_nearby_removed++;
                    }
                    neighbors_checked_count++;
                    if (neighbors_checked_count >= MAX_CONNECTIVITY_NEIGHBORS_TO_CHECK) break;
                }
            }
            float score = static_cast<float>(num_nearby_removed);
            score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * (std::abs(score) + 1.0f);
            customerScores.push_back({score, customerId});
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6 + 6 + 5 + 4 + 2 + 2 + 2) { 
        for (int customerId : customers) {
            float score = static_cast<float>(instance.prizes[customerId]);
            score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * std::abs(score + 1.0f);
            customerScores.push_back({score, customerId});
        }
    } else if (strategy_choice_category < 30 + 25 + 15 + 6 + 6 + 5 + 4 + 2 + 2 + 2 + 1) { 
        for (int customerId : customers) {
            float score = -static_cast<float>(instance.demand[customerId]);
            score += (getRandomFractionFast() * 2.0f - 1.0f) * SECONDARY_NOISE_FACTOR * (std::fabs(score) + 1.0f);
            customerScores.push_back({score, customerId});
        }
    } else {
        static thread_local std::mt19937 gen_shuffle_sort(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen_shuffle_sort);
        return;
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
    
    if (getRandomFractionFast() < REVERSE_ORDER_PROBABILITY) {
        std::reverse(customers.begin(), customers.end());
    }
}