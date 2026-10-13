#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>

#include "Utils.h"

static thread_local std::mt19937 random_generator_for_shuffle(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<bool> selected_flags(sol.instance.numCustomers + 1, false);
    std::vector<int> selectedCustomers_vec;

    int numCustomersToRemove = std::min((int)(sol.instance.numCustomers * 0.02) + getRandomNumber(0, 5), 30);
    numCustomersToRemove = std::max(5, numCustomersToRemove);

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }
    
    selectedCustomers_vec.reserve(numCustomersToRemove);

    int initial_customers_added = 0;
    if (getRandomFraction() < 0.20f && !sol.tours.empty() && numCustomersToRemove >= 3) {
        int random_tour_idx = getRandomNumber(0, static_cast<int>(sol.tours.size()) - 1);
        const Tour& selected_tour = sol.tours[random_tour_idx];
        if (selected_tour.customers.size() > 1) {
            int start_idx_in_tour = getRandomNumber(0, static_cast<int>(selected_tour.customers.size()) - 1);
            int segment_length_limit = std::min(numCustomersToRemove, getRandomNumber(2, 5));
            segment_length_limit = std::min(segment_length_limit, static_cast<int>(selected_tour.customers.size()));

            for (int i = 0; i < segment_length_limit && initial_customers_added < numCustomersToRemove; ++i) {
                int customer_id = selected_tour.customers[(start_idx_in_tour + i) % selected_tour.customers.size()];
                if (customer_id >= 1 && customer_id <= sol.instance.numCustomers && !selected_flags[customer_id]) {
                    selected_flags[customer_id] = true;
                    selectedCustomers_vec.push_back(customer_id);
                    initial_customers_added++;
                }
            }
        }
    }
    
    if (initial_customers_added == 0) {
        int seed_customer_id = -1;
        if (!sol.tours.empty()) {
            int random_tour_idx = getRandomNumber(0, static_cast<int>(sol.tours.size()) - 1);
            const Tour& selected_tour = sol.tours[random_tour_idx];
            if (!selected_tour.customers.empty()) {
                int seed_customer_idx_in_tour = getRandomNumber(0, static_cast<int>(selected_tour.customers.size()) - 1);
                seed_customer_id = selected_tour.customers[seed_customer_idx_in_tour];
            }
        } 
        if (seed_customer_id == -1 || seed_customer_id < 1 || seed_customer_id > sol.instance.numCustomers) {
            seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
        }
        if (!selected_flags[seed_customer_id]) {
            selected_flags[seed_customer_id] = true;
            selectedCustomers_vec.push_back(seed_customer_id);
        }
    }
    
    int last_added_customer_id = selectedCustomers_vec.empty() ? -1 : selectedCustomers_vec.back();

    int safety_attempts_outer = 0;
    const int MAX_SAFETY_ATTEMPTS_OUTER = numCustomersToRemove * 10 + 20;

    while (selectedCustomers_vec.size() < static_cast<size_t>(numCustomersToRemove) && safety_attempts_outer < MAX_SAFETY_ATTEMPTS_OUTER) {
        int chosen_customer = -1;
        int current_selected_anchor_id = last_added_customer_id;

        if (getRandomFraction() >= 0.65f && !selectedCustomers_vec.empty()) { 
            current_selected_anchor_id = selectedCustomers_vec[getRandomNumber(0, static_cast<int>(selectedCustomers_vec.size()) - 1)];
        }

        if (current_selected_anchor_id != -1 && current_selected_anchor_id >= 1 && current_selected_anchor_id <= sol.instance.numCustomers &&
            sol.customerToTourMap[current_selected_anchor_id] != -1 && getRandomFraction() < 0.60f) {
            int tour_idx = sol.customerToTourMap[current_selected_anchor_id];
            if (static_cast<size_t>(tour_idx) < sol.tours.size()) {
                const auto& tour_customers = sol.tours[tour_idx].customers;
                if (tour_customers.size() > 1) {
                    int idx_in_tour = -1;
                    for(size_t i = 0; i < tour_customers.size(); ++i) {
                        if (tour_customers[i] == current_selected_anchor_id) {
                            idx_in_tour = static_cast<int>(i);
                            break;
                        }
                    }
                    if (idx_in_tour != -1) {
                        for (int attempt = 0; attempt < 3; ++attempt) {
                            int offset = getRandomNumber(1, std::min(static_cast<int>(tour_customers.size()) - 1, 3)); 
                            int direction = (getRandomFraction() < 0.5) ? 1 : -1;
                            int neighbor_idx = (idx_in_tour + direction * offset + static_cast<int>(tour_customers.size())) % static_cast<int>(tour_customers.size());
                            int potential_customer = tour_customers[neighbor_idx];
                            if (potential_customer >= 1 && potential_customer <= sol.instance.numCustomers && !selected_flags[potential_customer]) {
                                chosen_customer = potential_customer;
                                break;
                            }
                        }
                    }
                }
            }
        }

        if (chosen_customer == -1 && current_selected_anchor_id != -1 && current_selected_anchor_id >= 1 && current_selected_anchor_id <= sol.instance.numCustomers &&
            static_cast<size_t>(current_selected_anchor_id) < sol.instance.adj.size()) { 
            std::vector<int> temp_neighbors;
            for (int i = 0; i < std::min(static_cast<int>(sol.instance.adj[current_selected_anchor_id].size()), 7); ++i) {
                int neighbor = sol.instance.adj[current_selected_anchor_id][i];
                if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && !selected_flags[neighbor]) {
                    temp_neighbors.push_back(neighbor);
                }
            }
            if (!temp_neighbors.empty()) {
                chosen_customer = temp_neighbors[getRandomNumber(0, static_cast<int>(temp_neighbors.size()) - 1)];
            }
        }
        
        if (chosen_customer == -1 && !selectedCustomers_vec.empty() && getRandomFraction() < 0.15f) { 
            int alt_anchor_id = selectedCustomers_vec[getRandomNumber(0, static_cast<int>(selectedCustomers_vec.size()) - 1)];
            if (alt_anchor_id != current_selected_anchor_id && alt_anchor_id >= 1 && alt_anchor_id <= sol.instance.numCustomers && 
                static_cast<size_t>(alt_anchor_id) < sol.instance.adj.size()) {
                
                std::vector<int> temp_neighbors;
                for (int i = 0; i < std::min(static_cast<int>(sol.instance.adj[alt_anchor_id].size()), 6); ++i) {
                    int neighbor = sol.instance.adj[alt_anchor_id][i];
                    if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && !selected_flags[neighbor]) {
                        temp_neighbors.push_back(neighbor);
                    }
                }
                if (!temp_neighbors.empty()) {
                    chosen_customer = temp_neighbors[getRandomNumber(0, static_cast<int>(temp_neighbors.size()) - 1)];
                }
            }
        }

        if (chosen_customer == -1) {
            int random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
            int safety_counter_random = 0;
            while (selected_flags[random_unselected_customer] && safety_counter_random < sol.instance.numCustomers * 2) {
                random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter_random++;
            }
            if (safety_counter_random < sol.instance.numCustomers * 2) {
                chosen_customer = random_unselected_customer;
            } else { 
                safety_attempts_outer++; 
                continue; 
            }
        }

        if (chosen_customer != -1 && !selected_flags[chosen_customer]) {
            selected_flags[chosen_customer] = true;
            selectedCustomers_vec.push_back(chosen_customer);
            last_added_customer_id = chosen_customer;
            safety_attempts_outer = 0; 
        } else {
            safety_attempts_outer++; 
        }
    }

    while (selectedCustomers_vec.size() < static_cast<size_t>(numCustomersToRemove)) {
        int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
        int safety_fill_counter = 0;
        const int MAX_FILL_ATTEMPTS = sol.instance.numCustomers * 2;
        while (selected_flags[rand_cust] && safety_fill_counter < MAX_FILL_ATTEMPTS) {
             rand_cust = getRandomNumber(1, sol.instance.numCustomers);
             safety_fill_counter++;
        }
        if (!selected_flags[rand_cust]) {
            selected_flags[rand_cust] = true;
            selectedCustomers_vec.push_back(rand_cust);
        } else {
            break;
        }
    }

    return selectedCustomers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float JITTER_MAGNITUDE = 1e-5f;
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());
    bool sort_ascending_final = true; 
    
    float min_tw_width = std::numeric_limits<float>::max();
    float max_tw_width = std::numeric_limits<float>::lowest();
    float min_demand = std::numeric_limits<float>::max();
    float max_demand = std::numeric_limits<float>::lowest();
    float min_dist_depot = std::numeric_limits<float>::max();
    float max_dist_depot = std::numeric_limits<float>::lowest();
    float min_service_time = std::numeric_limits<float>::max();
    float max_service_time = std::numeric_limits<float>::lowest();
    float min_start_tw = std::numeric_limits<float>::max();
    float max_start_tw = std::numeric_limits<float>::lowest();
    float min_end_tw = std::numeric_limits<float>::max();
    float max_end_tw = std::numeric_limits<float>::lowest();

    for (int customer_id : customers) { 
        min_tw_width = std::min(min_tw_width, instance.TW_Width[customer_id]);
        max_tw_width = std::max(max_tw_width, instance.TW_Width[customer_id]);
        min_demand = std::min(min_demand, static_cast<float>(instance.demand[customer_id]));
        max_demand = std::max(max_demand, static_cast<float>(instance.demand[customer_id]));
        min_dist_depot = std::min(min_dist_depot, instance.distanceMatrix[0][customer_id]);
        max_dist_depot = std::max(max_dist_depot, instance.distanceMatrix[0][customer_id]);
        min_service_time = std::min(min_service_time, instance.serviceTime[customer_id]);
        max_service_time = std::max(max_service_time, instance.serviceTime[customer_id]);
        min_start_tw = std::min(min_start_tw, instance.startTW[customer_id]);
        max_start_tw = std::max(max_start_tw, instance.startTW[customer_id]);
        min_end_tw = std::min(min_end_tw, instance.endTW[customer_id]);
        max_end_tw = std::max(max_end_tw, instance.endTW[customer_id]);
    }
    
    int strategy = getRandomNumber(0, 15); 

    if (strategy == 0) { 
        std::shuffle(customers.begin(), customers.end(), random_generator_for_shuffle);
        return; 
    }

    int pivot_customer_id = -1;
    if (strategy == 15 && !customers.empty()) { 
        pivot_customer_id = customers[getRandomNumber(0, static_cast<int>(customers.size()) - 1)];
        sort_ascending_final = (getRandomFraction() < 0.5f);
    }

    for (int customer_id : customers) {
        float score = 0.0f;
        switch (strategy) {
            case 1: { 
                float WEIGHT_TW_TIGHTNESS = 3.5f;    
                float WEIGHT_DEMAND = 2.0f;          
                float WEIGHT_DIST_DEPOT = 1.8f;      
                float WEIGHT_SERVICE_TIME = 1.2f;    
                float WEIGHT_START_TW = 2.5f;        
                float WEIGHT_END_TW = 1.5f;
                
                float normalized_tw_width = 0.0f;
                if (max_tw_width - min_tw_width > 1e-6f) normalized_tw_width = (instance.TW_Width[customer_id] - min_tw_width) / (max_tw_width - min_tw_width);
                score += WEIGHT_TW_TIGHTNESS * (1.0f - normalized_tw_width);

                float normalized_demand = 0.0f;
                if (max_demand - min_demand > 1e-6f) normalized_demand = (static_cast<float>(instance.demand[customer_id]) - min_demand) / (max_demand - min_demand);
                score += WEIGHT_DEMAND * normalized_demand;

                float normalized_dist_depot = 0.0f;
                if (max_dist_depot - min_dist_depot > 1e-6f) normalized_dist_depot = (instance.distanceMatrix[0][customer_id] - min_dist_depot) / (max_dist_depot - min_dist_depot);
                score += WEIGHT_DIST_DEPOT * normalized_dist_depot;

                float normalized_service_time = 0.0f;
                if (max_service_time - min_service_time > 1e-6f) normalized_service_time = (instance.serviceTime[customer_id] - min_service_time) / (max_service_time - min_service_time);
                score += WEIGHT_SERVICE_TIME * normalized_service_time;

                float normalized_start_tw = 0.0f;
                if (max_start_tw - min_start_tw > 1e-6f) normalized_start_tw = (instance.startTW[customer_id] - min_start_tw) / (max_start_tw - min_start_tw);
                score += WEIGHT_START_TW * (1.0f - normalized_start_tw);

                float normalized_end_tw = 0.0f;
                if (max_end_tw - min_end_tw > 1e-6f) normalized_end_tw = (instance.endTW[customer_id] - min_end_tw) / (max_end_tw - min_end_tw);
                score += WEIGHT_END_TW * (1.0f - normalized_end_tw);
                sort_ascending_final = false;
                break;
            }
            case 2: { 
                float WEIGHT_TW_TIGHTNESS = getRandomFraction(3.0f, 5.0f);    
                float WEIGHT_DEMAND = getRandomFraction(1.5f, 3.5f);          
                float WEIGHT_DIST_DEPOT = getRandomFraction(1.0f, 2.0f);      
                float WEIGHT_SERVICE_TIME = getRandomFraction(0.5f, 1.5f);    
                float WEIGHT_START_TW = getRandomFraction(2.0f, 4.0f);        
                float WEIGHT_END_TW = getRandomFraction(2.5f, 4.5f);          
                
                float normalized_tw_width = 0.0f;
                if (max_tw_width - min_tw_width > 1e-6f) normalized_tw_width = (instance.TW_Width[customer_id] - min_tw_width) / (max_tw_width - min_tw_width);
                score += WEIGHT_TW_TIGHTNESS * (1.0f - normalized_tw_width);

                float normalized_demand = 0.0f;
                if (max_demand - min_demand > 1e-6f) normalized_demand = (static_cast<float>(instance.demand[customer_id]) - min_demand) / (max_demand - min_demand);
                score += WEIGHT_DEMAND * normalized_demand;

                float normalized_dist_depot = 0.0f;
                if (max_dist_depot - min_dist_depot > 1e-6f) normalized_dist_depot = (instance.distanceMatrix[0][customer_id] - min_dist_depot) / (max_dist_depot - min_dist_depot);
                score += WEIGHT_DIST_DEPOT * normalized_dist_depot;

                float normalized_service_time = 0.0f;
                if (max_service_time - min_service_time > 1e-6f) normalized_service_time = (instance.serviceTime[customer_id] - min_service_time) / (max_service_time - min_service_time);
                score += WEIGHT_SERVICE_TIME * normalized_service_time;

                float normalized_start_tw = 0.0f;
                if (max_start_tw - min_start_tw > 1e-6f) normalized_start_tw = (instance.startTW[customer_id] - min_start_tw) / (max_start_tw - min_start_tw);
                score += WEIGHT_START_TW * (1.0f - normalized_start_tw);

                float normalized_end_tw = 0.0f;
                if (max_end_tw - min_end_tw > 1e-6f) normalized_end_tw = (instance.endTW[customer_id] - min_end_tw) / (max_end_tw - min_end_tw);
                score += WEIGHT_END_TW * (1.0f - normalized_end_tw);
                
                sort_ascending_final = (getRandomFraction() < 0.7f);
                break;
            }
            case 3: 
                score = instance.distanceMatrix[0][customer_id];
                sort_ascending_final = true; 
                break;
            case 4: 
                score = instance.distanceMatrix[0][customer_id];
                sort_ascending_final = false; 
                break;
            case 5: 
                score = instance.TW_Width[customer_id];
                sort_ascending_final = true; 
                break;
            case 6: 
                score = instance.TW_Width[customer_id];
                sort_ascending_final = false; 
                break;
            case 7: 
                score = instance.startTW[customer_id];
                sort_ascending_final = true; 
                break;
            case 8: 
                score = instance.startTW[customer_id];
                sort_ascending_final = false; 
                break;
            case 9: 
                score = static_cast<float>(instance.demand[customer_id]);
                sort_ascending_final = true; 
                break;
            case 10: 
                score = static_cast<float>(instance.demand[customer_id]);
                sort_ascending_final = false; 
                break;
            case 11: 
                score = instance.serviceTime[customer_id];
                sort_ascending_final = true; 
                break;
            case 12: 
                score = instance.serviceTime[customer_id];
                sort_ascending_final = false; 
                break;
            case 13: 
                score = instance.endTW[customer_id];
                sort_ascending_final = true; 
                break;
            case 14: 
                score = instance.endTW[customer_id];
                sort_ascending_final = false; 
                break;
            case 15: 
                score = (pivot_customer_id != -1) ? instance.distanceMatrix[pivot_customer_id][customer_id] : getRandomFraction();
                break;
        }
        score += getRandomFraction(-JITTER_MAGNITUDE, JITTER_MAGNITUDE);
        customer_scores.push_back({score, customer_id});
    }

    if (sort_ascending_final) {
        std::sort(customer_scores.begin(), customer_scores.end());
    } else {
        std::sort(customer_scores.begin(), customer_scores.end(), 
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
            return a.first > b.first;
        });
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }

    if (customers.size() > 1 && strategy != 0 && getRandomFraction() < 0.25f) { 
        int num_swaps_to_perform = getRandomNumber(0, std::min(static_cast<int>(customers.size() / 3), 3));
        num_swaps_to_perform = std::max(0, num_swaps_to_perform);
        
        for (int i = 0; i < num_swaps_to_perform; ++i) {
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            int idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            if (idx1 != idx2) {
                std::swap(customers[idx1], customers[idx2]);
            }
        }
    }
}