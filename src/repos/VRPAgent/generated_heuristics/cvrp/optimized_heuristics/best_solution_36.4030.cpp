#include "AgentDesigned.h"
#include <vector>
#include <algorithm>
#include <utility>
#include <limits>
#include <random>
#include <cmath> // For std::fmax

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 15;
    const int MAX_CUSTOMERS_TO_REMOVE = 25;
    const int MAX_SEED_ATTEMPTS = 150;
    const float PROB_SELECT_ADJACENT_TOUR_CUSTOMER = 0.7f;
    const int MIN_SPATIAL_NEIGHBORS_TO_CONSIDER = 10;
    const int MAX_SPATIAL_NEIGHBORS_TO_CONSIDER = 20;
    const float PROB_SELECT_SPATIAL_NEIGHBOR_BASE = 0.38f;
    const float PROB_SELECT_SPATIAL_NEIGHBOR_NOISE = 0.05f;
    const float PROB_SELECT_OTHER_TOUR_CUSTOMER = 0.25f;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    
    if (sol.instance.numCustomers == 0 || numCustomersToRemove == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    std::vector<bool> is_selected_flag(sol.instance.numCustomers + 1, false);
    std::vector<int> selected_customers_result;
    selected_customers_result.reserve(numCustomersToRemove);

    std::vector<int> currentExpansionCandidates;

    int initialSeed = getRandomNumber(1, sol.instance.numCustomers);
    is_selected_flag[initialSeed] = true;
    selected_customers_result.push_back(initialSeed);
    currentExpansionCandidates.push_back(initialSeed);

    int current_selected_count = 1;

    while (current_selected_count < numCustomersToRemove) {
        if (currentExpansionCandidates.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            int attemptCount = 0;
            while (is_selected_flag[newSeed] && attemptCount < MAX_SEED_ATTEMPTS && current_selected_count < sol.instance.numCustomers) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                attemptCount++;
            }
            if (is_selected_flag[newSeed] || current_selected_count == sol.instance.numCustomers) {
                break;
            }
            is_selected_flag[newSeed] = true;
            selected_customers_result.push_back(newSeed);
            currentExpansionCandidates.push_back(newSeed);
            current_selected_count++;
            if (current_selected_count >= numCustomersToRemove) {
                break;
            }
        }

        int idxToExpand = getRandomNumber(0, static_cast<int>(currentExpansionCandidates.size()) - 1);
        int expandFromCustomer = currentExpansionCandidates[idxToExpand];

        bool addedCustomerInThisIteration = false;
        
        int tour_idx = sol.customerToTourMap[expandFromCustomer];
        int customer_pos_in_tour = -1;
        if (tour_idx >= 0 && static_cast<size_t>(tour_idx) < sol.tours.size()) {
            const Tour& tour = sol.tours[tour_idx];
            for (size_t i = 0; i < tour.customers.size(); ++i) {
                if (tour.customers[i] == expandFromCustomer) {
                    customer_pos_in_tour = static_cast<int>(i);
                    break;
                }
            }

            if (customer_pos_in_tour != -1) {
                if (customer_pos_in_tour > 0) {
                    int pred = tour.customers[customer_pos_in_tour - 1];
                    if (pred != 0 && !is_selected_flag[pred]) {
                        if (getRandomFractionFast() < PROB_SELECT_ADJACENT_TOUR_CUSTOMER) {
                            is_selected_flag[pred] = true;
                            selected_customers_result.push_back(pred);
                            currentExpansionCandidates.push_back(pred);
                            addedCustomerInThisIteration = true;
                            current_selected_count++;
                            if (current_selected_count >= numCustomersToRemove) break;
                        }
                    }
                }
                if (current_selected_count < numCustomersToRemove && static_cast<size_t>(customer_pos_in_tour) < tour.customers.size() - 1) {
                    int succ = tour.customers[customer_pos_in_tour + 1];
                    if (succ != 0 && !is_selected_flag[succ]) {
                        if (getRandomFractionFast() < PROB_SELECT_ADJACENT_TOUR_CUSTOMER) {
                            is_selected_flag[succ] = true;
                            selected_customers_result.push_back(succ);
                            currentExpansionCandidates.push_back(succ);
                            addedCustomerInThisIteration = true;
                            current_selected_count++;
                            if (current_selected_count >= numCustomersToRemove) break;
                        }
                    }
                }
            }
        }
        if (current_selected_count >= numCustomersToRemove) break;

        const auto& spatialNeighbors = sol.instance.adj[expandFromCustomer];
        int numSpatialNeighborsToConsider = std::min(static_cast<int>(spatialNeighbors.size()), getRandomNumber(MIN_SPATIAL_NEIGHBORS_TO_CONSIDER, MAX_SPATIAL_NEIGHBORS_TO_CONSIDER));
        float prob_select_spatial_neighbor = PROB_SELECT_SPATIAL_NEIGHBOR_BASE + getRandomFractionFast() * PROB_SELECT_SPATIAL_NEIGHBOR_NOISE;
        for (int i = 0; i < numSpatialNeighborsToConsider; ++i) {
            int neighbor = spatialNeighbors[i];
            if (neighbor == 0) continue;

            if (!is_selected_flag[neighbor]) {
                if (getRandomFractionFast() < prob_select_spatial_neighbor) {
                    is_selected_flag[neighbor] = true;
                    selected_customers_result.push_back(neighbor);
                    currentExpansionCandidates.push_back(neighbor);
                    addedCustomerInThisIteration = true;
                    current_selected_count++;
                    if (current_selected_count >= numCustomersToRemove) break;
                }
            }
        }
        if (current_selected_count >= numCustomersToRemove) break;

        if (tour_idx >= 0 && static_cast<size_t>(tour_idx) < sol.tours.size()) {
            const Tour& tour = sol.tours[tour_idx];
            for (int customer_in_tour : tour.customers) {
                if (customer_in_tour == 0 || customer_in_tour == expandFromCustomer) continue;

                bool is_direct_neighbor = false;
                if (customer_pos_in_tour != -1) {
                    if ((customer_pos_in_tour > 0 && tour.customers[customer_pos_in_tour - 1] == customer_in_tour) ||
                        (static_cast<size_t>(customer_pos_in_tour) < tour.customers.size() - 1 && tour.customers[customer_pos_in_tour + 1] == customer_in_tour)) {
                        is_direct_neighbor = true;
                    }
                }
                
                if (!is_selected_flag[customer_in_tour] && !is_direct_neighbor) {
                    if (getRandomFractionFast() < PROB_SELECT_OTHER_TOUR_CUSTOMER) {
                        is_selected_flag[customer_in_tour] = true;
                        selected_customers_result.push_back(customer_in_tour);
                        currentExpansionCandidates.push_back(customer_in_tour);
                        addedCustomerInThisIteration = true;
                        current_selected_count++;
                        if (current_selected_count >= numCustomersToRemove) break;
                    }
                }
            }
        }
        if (current_selected_count >= numCustomersToRemove) break;

        if (!addedCustomerInThisIteration) {
            if (!currentExpansionCandidates.empty()) {
                std::swap(currentExpansionCandidates[idxToExpand], currentExpansionCandidates.back());
                currentExpansionCandidates.pop_back();
            }
        }
    }

    return selected_customers_result;
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float SORT_PERTURBATION_FACTOR = 0.00005f;
    const float PROB_SORT_BY_ANCHOR_DISTANCE = 0.70f;
    const float PROB_ANCHOR_SORT_ASCENDING = 0.5f;
    const float PROB_ANCHOR_CLOSEST_TO_DEPOT = 0.15f;
    const float PROB_SORT_BY_COMBINED_SCORE = 0.25f;
    const float DEMAND_WEIGHT_BASE = 0.5f;
    const float DEMAND_WEIGHT_NOISE_RANGE = 0.4f;
    const float SCORE_NOISE_FACTOR = 0.2f;
    const float DEGREE_INFLUENCE_FACTOR_MAX = 0.35f;
    const float PROB_RANDOM_SHUFFLE_IMPLIED = 1.0f - (PROB_SORT_BY_ANCHOR_DISTANCE + PROB_SORT_BY_COMBINED_SCORE);
    const float PROB_RANDOM_SWAPS = 0.15f;
    const int MIN_SWAPS = 1;
    const int MAX_SWAPS_RELATIVE_TO_SIZE = 4;
    const int MAX_ABSOLUTE_SWAPS = 6;

    static float max_overall_dist_from_depot = -1.0f;
    static float max_overall_demand_cached = -1.0f;
    static float max_overall_degree_cached = -1.0f;

    if (max_overall_dist_from_depot < 0) {
        max_overall_dist_from_depot = 0.0f;
        for (int i = 1; i <= instance.numCustomers; ++i) {
            if (instance.distanceMatrix[0][i] > max_overall_dist_from_depot) {
                max_overall_dist_from_depot = instance.distanceMatrix[0][i];
            }
        }
        max_overall_dist_from_depot = std::fmax(max_overall_dist_from_depot, 1.0f);
    }
    if (max_overall_demand_cached < 0) {
         max_overall_demand_cached = static_cast<float>(instance.vehicleCapacity);
         max_overall_demand_cached = std::fmax(max_overall_demand_cached, 1.0f);
    }
    if (max_overall_degree_cached < 0) {
        max_overall_degree_cached = 0.0f;
        for (int i = 1; i <= instance.numCustomers; ++i) {
            if (static_cast<float>(instance.adj[i].size()) > max_overall_degree_cached) {
                max_overall_degree_cached = static_cast<float>(instance.adj[i].size());
            }
        }
        max_overall_degree_cached = std::fmax(max_overall_degree_cached, 1.0f);
    }

    float p_strategy = getRandomFractionFast();

    if (p_strategy < PROB_SORT_BY_ANCHOR_DISTANCE) { 
        int anchorCustomer;
        if (getRandomFractionFast() < PROB_ANCHOR_CLOSEST_TO_DEPOT) {
            float minDepotDist = std::numeric_limits<float>::max();
            int closestToDepotCustomer = -1;

            for (int customer_id : customers) {
                float dist = instance.distanceMatrix[0][customer_id];
                if (dist < minDepotDist) {
                    minDepotDist = dist;
                    closestToDepotCustomer = customer_id;
                }
            }
            if (closestToDepotCustomer != -1) {
                anchorCustomer = closestToDepotCustomer;
            } else {
                int anchorCustomerIdx = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
                anchorCustomer = customers[anchorCustomerIdx];
            }
        } else {
            int anchorCustomerIdx = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            anchorCustomer = customers[anchorCustomerIdx];
        }

        std::vector<std::pair<float, int>> customerDistances;
        customerDistances.reserve(customers.size());
        for (int customer_id : customers) {
            customerDistances.push_back({instance.distanceMatrix[anchorCustomer][customer_id] + getRandomFractionFast() * SORT_PERTURBATION_FACTOR, customer_id});
        }

        bool sortAscending = (getRandomFractionFast() < PROB_ANCHOR_SORT_ASCENDING);

        if (sortAscending) {
            std::sort(customerDistances.begin(), customerDistances.end());
        } else {
            std::sort(customerDistances.begin(), customerDistances.end(), std::greater<std::pair<float, int>>());
        }

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customerDistances[i].second;
        }
    } else if (p_strategy < PROB_SORT_BY_ANCHOR_DISTANCE + PROB_SORT_BY_COMBINED_SCORE) {
        std::vector<std::pair<float, int>> scored_customers;
        scored_customers.reserve(customers.size());

        float alpha_demand_dist = DEMAND_WEIGHT_BASE + (getRandomFractionFast() - 0.5f) * DEMAND_WEIGHT_NOISE_RANGE;
        alpha_demand_dist = std::fmax(0.0f, std::fmin(1.0f, alpha_demand_dist));

        float scoringStrategyChoice = getRandomFractionFast();
        float noise_factor = SCORE_NOISE_FACTOR; 
        float degree_influence_factor = getRandomFractionFast() * DEGREE_INFLUENCE_FACTOR_MAX;

        for (int customer_id : customers) {
            float current_demand = static_cast<float>(instance.demand[customer_id]);
            float current_dist_from_depot = instance.distanceMatrix[0][customer_id];
            float current_degree = static_cast<float>(instance.adj[customer_id].size());

            float normalized_demand = current_demand / max_overall_demand_cached;
            float normalized_dist = current_dist_from_depot / max_overall_dist_from_depot;
            float normalized_degree = current_degree / max_overall_degree_cached;

            float base_score_demand_dist;
            if (scoringStrategyChoice < 0.5f) {
                base_score_demand_dist = normalized_demand * alpha_demand_dist + normalized_dist * (1.0f - alpha_demand_dist);
            } else if (scoringStrategyChoice < 0.75f) {
                base_score_demand_dist = normalized_demand;
            } else {
                base_score_demand_dist = normalized_dist;
            }
            
            float final_score_without_noise = base_score_demand_dist * (1.0f - degree_influence_factor) + normalized_degree * degree_influence_factor;

            float random_noise = (getRandomFractionFast() - 0.5f) * noise_factor;
            float final_score = final_score_without_noise + random_noise + getRandomFractionFast() * SORT_PERTURBATION_FACTOR;
            
            scored_customers.push_back({final_score, customer_id});
        }

        std::sort(scored_customers.begin(), scored_customers.end(), 
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
            return a.first > b.first;
        });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scored_customers[i].second;
        }
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }

    if (customers.size() > 1 && getRandomFractionFast() < PROB_RANDOM_SWAPS) {
        int numSwaps = getRandomNumber(MIN_SWAPS, std::min(static_cast<int>(customers.size()) / MAX_SWAPS_RELATIVE_TO_SIZE, MAX_ABSOLUTE_SWAPS));
        for (int i = 0; i < numSwaps; ++i) {
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            int idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            if (idx1 != idx2) {
                std::swap(customers[idx1], customers[idx2]);
            }
        }
    }
}