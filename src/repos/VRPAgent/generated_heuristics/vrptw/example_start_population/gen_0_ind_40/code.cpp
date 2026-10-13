#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <deque> // For std::deque for efficient front removal
#include <cmath> // For std::fmax (optional, not strictly needed with 0.01f offset)
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> customers_to_return;

    int max_customers_to_remove = getRandomNumber(15, 30); 
    
    if (sol.instance.numCustomers == 0) {
        return customers_to_return;
    }
    
    std::vector<int> all_customers_in_solution;
    all_customers_in_solution.reserve(sol.instance.numCustomers); 
    for (const Tour& tour : sol.tours) {
        for (int customer_id : tour.customers) {
            all_customers_in_solution.push_back(customer_id);
        }
    }

    if (all_customers_in_solution.empty()) {
        return customers_to_return;
    }

    if (max_customers_to_remove > (int)all_customers_in_solution.size()) {
        max_customers_to_remove = (int)all_customers_in_solution.size();
    }

    if (max_customers_to_remove == 0) {
        return customers_to_return;
    }

    int seed_customer_idx = getRandomNumber(0, (int)all_customers_in_solution.size() - 1);
    int seed_customer_id = all_customers_in_solution[seed_customer_idx];

    selected_customers_set.insert(seed_customer_id);
    customers_to_return.push_back(seed_customer_id);

    std::deque<int> expansion_queue; 
    expansion_queue.push_back(seed_customer_id);

    const float PROB_ADD_GEOGRAPHIC_NEIGHBOR = 0.7f; 
    const float PROB_ADD_TOUR_NEIGHBOR = 0.9f; 
    const float PROB_ADD_RANDOM_CUSTOMER = 0.03f; 

    while (selected_customers_set.size() < max_customers_to_remove && !expansion_queue.empty()) {
        int current_customer_id = expansion_queue.front();
        expansion_queue.pop_front();

        if (current_customer_id > 0 && current_customer_id < sol.instance.numNodes) { 
            for (int neighbor_node_id : sol.instance.adj[current_customer_id]) {
                if (neighbor_node_id == 0) continue; 
                if (selected_customers_set.find(neighbor_node_id) == selected_customers_set.end()) {
                    if (getRandomFractionFast() < PROB_ADD_GEOGRAPHIC_NEIGHBOR) {
                        selected_customers_set.insert(neighbor_node_id);
                        customers_to_return.push_back(neighbor_node_id);
                        expansion_queue.push_back(neighbor_node_id);
                        if (selected_customers_set.size() >= max_customers_to_remove) {
                            return customers_to_return;
                        }
                    }
                }
            }
        }
        
        if (current_customer_id < sol.customerToTourMap.size()) { 
            int current_tour_idx = sol.customerToTourMap[current_customer_id];
            if (current_tour_idx != -1 && current_tour_idx < sol.tours.size()) {
                const Tour& tour = sol.tours[current_tour_idx];
                for (size_t i = 0; i < tour.customers.size(); ++i) {
                    if (tour.customers[i] == current_customer_id) {
                        if (i > 0) { 
                            int prev_customer_id = tour.customers[i - 1];
                            if (selected_customers_set.find(prev_customer_id) == selected_customers_set.end()) {
                                if (getRandomFractionFast() < PROB_ADD_TOUR_NEIGHBOR) {
                                    selected_customers_set.insert(prev_customer_id);
                                    customers_to_return.push_back(prev_customer_id);
                                    expansion_queue.push_back(prev_customer_id);
                                    if (selected_customers_set.size() >= max_customers_to_remove) {
                                        return customers_to_return;
                                    }
                                }
                            }
                        }
                        if (i < tour.customers.size() - 1) { 
                            int next_customer_id = tour.customers[i + 1];
                            if (selected_customers_set.find(next_customer_id) == selected_customers_set.end()) {
                                if (getRandomFractionFast() < PROB_ADD_TOUR_NEIGHBOR) {
                                    selected_customers_set.insert(next_customer_id);
                                    customers_to_return.push_back(next_customer_id);
                                    expansion_queue.push_back(next_customer_id);
                                    if (selected_customers_set.size() >= max_customers_to_remove) {
                                        return customers_to_return;
                                    }
                                }
                            }
                        }
                        break; 
                    }
                }
            }
        }

        if (getRandomFractionFast() < PROB_ADD_RANDOM_CUSTOMER && selected_customers_set.size() < max_customers_to_remove) {
            int random_customer_id_idx = getRandomNumber(0, (int)all_customers_in_solution.size() - 1);
            int random_customer_id = all_customers_in_solution[random_customer_id_idx];
            if (selected_customers_set.find(random_customer_id) == selected_customers_set.end()) {
                selected_customers_set.insert(random_customer_id);
                customers_to_return.push_back(random_customer_id);
                if (selected_customers_set.size() >= max_customers_to_remove) {
                    return customers_to_return;
                }
            }
        }
    }

    while (selected_customers_set.size() < max_customers_to_remove) {
        int random_customer_id_idx = getRandomNumber(0, (int)all_customers_in_solution.size() - 1);
        int random_customer_id = all_customers_in_solution[random_customer_id_idx];
        if (selected_customers_set.find(random_customer_id) == selected_customers_set.end()) {
            selected_customers_set.insert(random_customer_id);
            customers_to_return.push_back(random_customer_id);
        }
    }

    return customers_to_return;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float WEIGHT_TW_TIGHTNESS = 1000.0f; 
    const float WEIGHT_SERVICE_TIME = 10.0f;
    const float WEIGHT_DEMAND = 5.0f;
    const float WEIGHT_DISTANCE_FROM_DEPOT = 1.0f;
    
    const float STOCHASTIC_FACTOR = 50.0f; 

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = 0.0f;

        float tw_width = instance.TW_Width[customer_id];
        score += (1.0f / (tw_width + 0.01f)) * WEIGHT_TW_TIGHTNESS; 

        score += instance.serviceTime[customer_id] * WEIGHT_SERVICE_TIME;
        score += instance.demand[customer_id] * WEIGHT_DEMAND;
        score += instance.distanceMatrix[0][customer_id] * WEIGHT_DISTANCE_FROM_DEPOT;

        score += getRandomFractionFast() * STOCHASTIC_FACTOR;

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; 
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}