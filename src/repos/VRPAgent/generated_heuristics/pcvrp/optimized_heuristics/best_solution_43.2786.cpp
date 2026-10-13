#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <numeric> // Required for std::iota if used, but not for the selected approach
#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE_LLM = 10;
const int MAX_CUSTOMERS_TO_REMOVE_LLM = 20;
const int NEIGHBOR_SELECTION_LIMIT_LLM = 5;

const float PROB_UNVISITED_SEED_LLM = 0.25f;
const float PROB_TOUR_BASED_SEED_LLM = 0.6f;
const int MAX_TOUR_SEED_ATTEMPTS_LLM = 5;

const int MIN_SOURCE_CUSTOMERS_TO_CHECK_LLM = 1;
const int MAX_SOURCE_CUSTOMERS_TO_CHECK_LLM = 4;
const int MAX_TOUR_CUSTOMERS_TO_CONSIDER_LLM = 4;

const int MAX_SAFETY_ATTEMPTS_LLM = 500 * 2; 

static thread_local std::mt19937 gen_llm(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selectedCustomersList;
    std::vector<char> is_customer_selected(sol.instance.numCustomers + 1, 0); 

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE_LLM, MAX_CUSTOMERS_TO_REMOVE_LLM);

    if (numCustomersToRemove == 0) return {};
    if (sol.instance.numCustomers == 0) return {};

    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    int initial_seed = -1;

    if (getRandomFractionFast() < PROB_UNVISITED_SEED_LLM) {
        std::vector<int> unvisited_customers;
        unvisited_customers.reserve(sol.instance.numCustomers / 10);
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (sol.customerToTourMap[i] == -1) {
                unvisited_customers.push_back(i);
            }
        }
        if (!unvisited_customers.empty()) {
            initial_seed = unvisited_customers[getRandomNumber(0, unvisited_customers.size() - 1)];
        }
    }
    
    if (initial_seed == -1 && getRandomFractionFast() < PROB_TOUR_BASED_SEED_LLM && !sol.tours.empty()) {
        int attempts = 0;
        while (initial_seed == -1 && attempts < MAX_TOUR_SEED_ATTEMPTS_LLM) {
            int random_tour_idx = getRandomNumber(0, sol.tours.size() - 1);
            const Tour& chosen_tour = sol.tours[random_tour_idx];
            if (!chosen_tour.customers.empty()) {
                int random_cust_in_tour_idx = getRandomNumber(0, chosen_tour.customers.size() - 1);
                initial_seed = chosen_tour.customers[random_cust_in_tour_idx];
            }
            attempts++;
        }
    }

    if (initial_seed == -1) {
        initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    selectedCustomersList.push_back(initial_seed);
    is_customer_selected[initial_seed] = 1;

    std::vector<int> candidates_for_next_selection;
    // Reserve enough space to avoid reallocations. Max sources * (max neighbors + max tour customers)
    candidates_for_next_selection.reserve(MAX_SOURCE_CUSTOMERS_TO_CHECK_LLM * (NEIGHBOR_SELECTION_LIMIT_LLM + MAX_TOUR_CUSTOMERS_TO_CONSIDER_LLM)); 

    // Use a fixed-size array to track which source customers have been picked for the current iteration
    // This avoids copying and shuffling 'selectedCustomersList' repeatedly.
    bool source_idx_picked_for_this_iter[MAX_CUSTOMERS_TO_REMOVE_LLM]; // Max index will be MAX_CUSTOMERS_TO_REMOVE_LLM - 1

    while (selectedCustomersList.size() < numCustomersToRemove) {
        candidates_for_next_selection.clear();
        std::fill(source_idx_picked_for_this_iter, source_idx_picked_for_this_iter + MAX_CUSTOMERS_TO_REMOVE_LLM, false);

        int num_source_customers_to_check = std::min((int)selectedCustomersList.size(), 
                                                      getRandomNumber(MIN_SOURCE_CUSTOMERS_TO_CHECK_LLM, MAX_SOURCE_CUSTOMERS_TO_CHECK_LLM)); 
        
        for (int i = 0; i < num_source_customers_to_check; ++i) {
            int source_customer_idx_in_selected_list = -1;
            int safety_attempts_for_source_pick = 0;
            // Find a unique index from selectedCustomersList to use as a source
            while (safety_attempts_for_source_pick < selectedCustomersList.size() * 2) { 
                int potential_idx = getRandomNumber(0, selectedCustomersList.size() - 1);
                if (!source_idx_picked_for_this_iter[potential_idx]) {
                    source_customer_idx_in_selected_list = potential_idx;
                    source_idx_picked_for_this_iter[potential_idx] = true;
                    break;
                }
                safety_attempts_for_source_pick++;
            }

            if (source_customer_idx_in_selected_list == -1) {
                // If we can't find enough unique sources after reasonable attempts, break early.
                break; 
            }

            int source_customer = selectedCustomersList[source_customer_idx_in_selected_list];

            int num_neighbors = sol.instance.adj[source_customer].size();
            for (int neighbor_idx = 0; neighbor_idx < std::min(num_neighbors, NEIGHBOR_SELECTION_LIMIT_LLM); ++neighbor_idx) {
                int neighbor = sol.instance.adj[source_customer][neighbor_idx];
                if (is_customer_selected[neighbor] == 0) { 
                    candidates_for_next_selection.push_back(neighbor);
                }
            }
            
            if (sol.customerToTourMap[source_customer] != -1) {
                const Tour& tour = sol.tours[sol.customerToTourMap[source_customer]];
                
                if (!tour.customers.empty()) { 
                    int num_customers_in_tour = tour.customers.size();
                    int num_tour_customers_to_sample = std::min(num_customers_in_tour, MAX_TOUR_CUSTOMERS_TO_CONSIDER_LLM);
                    
                    for (int k = 0; k < num_tour_customers_to_sample; ++k) {
                        int random_idx = getRandomNumber(0, num_customers_in_tour - 1);
                        int tour_customer = tour.customers[random_idx];
                        if (tour_customer != source_customer && is_customer_selected[tour_customer] == 0) {
                            candidates_for_next_selection.push_back(tour_customer);
                        }
                    }
                }
            }
        }

        if (candidates_for_next_selection.empty()) {
            int random_customer_candidate = -1;
            int safety_counter = 0;
            
            do {
                random_customer_candidate = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter++;
            } while (is_customer_selected[random_customer_candidate] == 1 && safety_counter < MAX_SAFETY_ATTEMPTS_LLM); 
            
            if (random_customer_candidate != -1 && is_customer_selected[random_customer_candidate] == 0) { 
                selectedCustomersList.push_back(random_customer_candidate);
                is_customer_selected[random_customer_candidate] = 1;
            } else {
                break; 
            }
        } else {
            int chosen_customer = candidates_for_next_selection[getRandomNumber(0, candidates_for_next_selection.size() - 1)];
            selectedCustomersList.push_back(chosen_customer);
            is_customer_selected[chosen_customer] = 1;
        }
    }

    return selectedCustomersList;
}

const float PROB_PIVOT_IS_REMOVED_CUSTOMER_LLM = 0.8f;
const float PROB_SORT_DESCENDING_LLM = 0.5f;
const float PROB_PURE_SHUFFLE_LLM = 0.1f;

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float sorting_strategy_choice = getRandomFractionFast();
    bool sort_descending = (getRandomFractionFast() < PROB_SORT_DESCENDING_LLM);

    if (sorting_strategy_choice < PROB_PURE_SHUFFLE_LLM) { 
        std::shuffle(customers.begin(), customers.end(), gen_llm);
        return;
    }

    int pivot_node_id;
    if (getRandomFractionFast() < PROB_PIVOT_IS_REMOVED_CUSTOMER_LLM) { 
        pivot_node_id = customers[getRandomNumber(0, customers.size() - 1)];
    } else { 
        pivot_node_id = 0; // Depot
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Base weights for scoring components
    float base_prize_weight = 0.2f; 
    float base_depot_distance_weight = 0.005f; 
    float base_jitter_scale = 0.0001f; 
    float base_demand_weight = 0.0f;

    // Introduce variability in weights based on sorting_strategy_choice
    float sub_strategy_bias = (sorting_strategy_choice - PROB_PURE_SHUFFLE_LLM) / (1.0f - PROB_PURE_SHUFFLE_LLM);

    if (sub_strategy_bias < 0.45f) {
        base_prize_weight *= (1.5f + getRandomFractionFast() * 0.5f);
        base_depot_distance_weight *= (0.5f + getRandomFractionFast() * 0.2f);
        base_jitter_scale *= (0.8f + getRandomFractionFast() * 0.4f);
    } else if (sub_strategy_bias < 0.8f) {
        base_prize_weight *= (0.6f + getRandomFractionFast() * 0.3f);
        base_depot_distance_weight *= (0.6f + getRandomFractionFast() * 0.3f);
        base_jitter_scale *= (1.2f + getRandomFractionFast() * 0.6f);
    } else {
        base_depot_distance_weight *= (2.0f + getRandomFractionFast() * 1.0f);
        base_prize_weight *= (0.4f + getRandomFractionFast() * 0.2f);
        base_demand_weight = 0.01f + getRandomFractionFast() * 0.02f;
        base_jitter_scale *= (1.5f + getRandomFractionFast() * 0.5f);
    }

    for (int customer_id : customers) {
        float distance_to_pivot_score = instance.distanceMatrix[customer_id][pivot_node_id];
        float prize_score_component = -instance.prizes[customer_id] * base_prize_weight;
        float depot_distance_component = instance.distanceMatrix[0][customer_id] * base_depot_distance_weight;
        float demand_component = instance.demand[customer_id] * base_demand_weight;
        float random_jitter = getRandomFractionFast() * base_jitter_scale; 

        float combined_score = distance_to_pivot_score + prize_score_component + depot_distance_component + demand_component + random_jitter;
        scored_customers.push_back({combined_score, customer_id});
    }

    if (sort_descending) {
        std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
    } else {
        std::sort(scored_customers.begin(), scored_customers.end());
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}