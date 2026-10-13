#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort
#include <vector>    // Redundant but good practice
#include <utility>   // For std::pair
#include "Utils.h"   // Assumed to provide getRandomNumber, getRandomFraction etc.


std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 5;
    const int MAX_CUSTOMERS_TO_REMOVE = 20;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    std::unordered_set<int> selectedCustomers;

    int initial_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initial_seed_customer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int anchor_customer_idx_in_set = getRandomNumber(0, static_cast<int>(selectedCustomers.size()) - 1);
        auto it = selectedCustomers.begin();
        std::advance(it, anchor_customer_idx_in_set);
        int anchor_customer = *it;

        int candidate_customer = -1;
        bool found_suitable_candidate = false;

        const float P_TOUR_BASED = 0.7f;
        if (getRandomFraction() < P_TOUR_BASED) {
            if (sol.customerToTourMap.count(anchor_customer) && 
                static_cast<size_t>(sol.customerToTourMap.at(anchor_customer)) < sol.tours.size()) {
                
                const Tour& current_tour = sol.tours[sol.customerToTourMap.at(anchor_customer)];
                if (!current_tour.customers.empty()) {
                    for (int attempts = 0; attempts < 5; ++attempts) {
                        int tour_customer_idx = getRandomNumber(0, static_cast<int>(current_tour.customers.size()) - 1);
                        int temp_candidate = current_tour.customers[tour_customer_idx];
                        if (selectedCustomers.find(temp_candidate) == selectedCustomers.end()) {
                            candidate_customer = temp_candidate;
                            found_suitable_candidate = true;
                            break;
                        }
                    }
                }
            }
        }

        if (!found_suitable_candidate) {
            const std::vector<int>& nearest_neighbors = sol.instance.adj[anchor_customer];
            if (!nearest_neighbors.empty()) {
                const int MAX_NEIGHBORS_TO_CONSIDER = 10; 
                int effective_neighbors_count = std::min(static_cast<int>(nearest_neighbors.size()), MAX_NEIGHBORS_TO_CONSIDER);

                for (int attempts = 0; attempts < 5; ++attempts) {
                    if (effective_neighbors_count == 0) break; 
                    int neighbor_idx = getRandomNumber(0, effective_neighbors_count - 1);
                    int temp_candidate = nearest_neighbors[neighbor_idx];
                    if (selectedCustomers.find(temp_candidate) == selectedCustomers.end()) {
                        candidate_customer = temp_candidate;
                        found_suitable_candidate = true;
                        break;
                    }
                }
            }
        }
        
        if (!found_suitable_candidate) {
            for (int attempts = 0; attempts < 10; ++attempts) { 
                int temp_candidate = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(temp_candidate) == selectedCustomers.end()) {
                    candidate_customer = temp_candidate;
                    found_suitable_candidate = true;
                    break;
                }
            }
            if (!found_suitable_candidate) {
                break; 
            }
        }
        
        selectedCustomers.insert(candidate_customer);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    enum SortCriteria {
        TW_TIGHTNESS,     
        DIST_TO_DEPOT,    
        DEMAND,           
        SERVICE_TIME,     
        RANDOM_ORDER      
    };

    SortCriteria chosen_criteria;
    float r = getRandomFraction();
    if (r < 0.30f) { 
        chosen_criteria = TW_TIGHTNESS;
    } else if (r < 0.60f) { 
        chosen_criteria = DIST_TO_DEPOT;
    } else if (r < 0.75f) { 
        chosen_criteria = DEMAND;
    } else if (r < 0.90f) { 
        chosen_criteria = SERVICE_TIME;
    } else { 
        chosen_criteria = RANDOM_ORDER;
    }

    if (chosen_criteria == RANDOM_ORDER) {
        static thread_local std::mt19937 gen(std::random_device{}()); 
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score_value;
        float perturbation = getRandomFraction() * 0.0001f; 

        switch (chosen_criteria) {
            case TW_TIGHTNESS:
                score_value = (instance.TW_Width[customer_id] > 0.001f) ? (1.0f / instance.TW_Width[customer_id]) : 100000.0f;
                break;
            case DIST_TO_DEPOT:
                score_value = instance.distanceMatrix[0][customer_id];
                break;
            case DEMAND:
                score_value = static_cast<float>(instance.demand[customer_id]);
                break;
            case SERVICE_TIME:
                score_value = instance.serviceTime[customer_id];
                break;
            default: 
                score_value = 0.0f;
                break;
        }
        customer_scores.push_back({score_value + perturbation, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}