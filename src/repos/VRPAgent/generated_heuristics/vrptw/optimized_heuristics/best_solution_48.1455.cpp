#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <utility>
#include <cmath>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int LLM_SELECT_MIN_CUSTOMERS_TO_REMOVE = 7;
    const int LLM_SELECT_MAX_CUSTOMERS_TO_REMOVE = 15;
    const int LLM_SELECT_MAX_ADD_ATTEMPTS = 76;
    const float LLM_SELECT_PROB_INITIAL_FROM_TOUR = 0.72f;
    const int LLM_SELECT_MAX_INITIAL_TOUR_ATTEMPTS = 50;
    const float LLM_SELECT_PROB_PICK_TOUR_ADJACENT = 0.65f;
    const float LLM_SELECT_PROB_PICK_ANY_FROM_TOUR_IF_ADJ_FAILS = 0.24f;
    const int LLM_SELECT_NUM_SPATIAL_NEIGHBORS_TO_CONSIDER = 20;
    const float LLM_SELECT_SPATIAL_SELECTION_BIAS_POWER = 2.8f;
    const float LLM_SELECT_PROB_SPATIAL_RANDOM_POOL_SELECTION = 0.14f;
    const int LLM_SELECT_SPATIAL_RANDOM_POOL_SIZE_MIN = 3;
    const int LLM_SELECT_SPATIAL_RANDOM_POOL_SIZE_MAX = 8;
    const int LLM_SELECT_FALLBACK_RANDOM_ATTEMPTS = 5;

    std::vector<int> selectedCustomersList;
    selectedCustomersList.reserve(LLM_SELECT_MAX_CUSTOMERS_TO_REMOVE);

    std::vector<char> isCustomerSelected(sol.instance.numCustomers + 1, 0);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int numCustomersToRemove = getRandomNumber(LLM_SELECT_MIN_CUSTOMERS_TO_REMOVE, LLM_SELECT_MAX_CUSTOMERS_TO_REMOVE);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int initial_customer = -1;
    bool initial_customer_found_in_tour = false;
    if (!sol.tours.empty() && getRandomFractionFast() < LLM_SELECT_PROB_INITIAL_FROM_TOUR) {
        int attempts = 0;
        while (attempts < LLM_SELECT_MAX_INITIAL_TOUR_ATTEMPTS) {
            int randomTourIdx = getRandomNumber(0, (int)sol.tours.size() - 1);
            if (!sol.tours[randomTourIdx].customers.empty()) {
                initial_customer = sol.tours[randomTourIdx].customers[getRandomNumber(0, (int)sol.tours[randomTourIdx].customers.size() - 1)];
                initial_customer_found_in_tour = true;
                break;
            }
            attempts++;
        }
    }
    if (!initial_customer_found_in_tour || initial_customer == -1) {
        initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    selectedCustomersList.push_back(initial_customer);
    isCustomerSelected[initial_customer] = 1;

    std::vector<std::pair<float, int>> potentialNeighborsWithDist;
    potentialNeighborsWithDist.reserve(LLM_SELECT_NUM_SPATIAL_NEIGHBORS_TO_CONSIDER);

    int current_attempts_overall = 0;
    while (selectedCustomersList.size() < static_cast<size_t>(numCustomersToRemove) && current_attempts_overall < LLM_SELECT_MAX_ADD_ATTEMPTS) {
        bool added_customer_in_this_attempt = false;
        int source_customer = selectedCustomersList[getRandomNumber(0, (int)selectedCustomersList.size() - 1)];

        int tour_idx = sol.customerToTourMap[source_customer];
        if (tour_idx != -1 && static_cast<size_t>(tour_idx) < sol.tours.size()) {
            const Tour& tour = sol.tours[tour_idx];
            if (tour.customers.size() > 1) {
                if (getRandomFractionFast() < LLM_SELECT_PROB_PICK_TOUR_ADJACENT) {
                    for (size_t i = 0; i < tour.customers.size(); ++i) {
                        if (tour.customers[i] == source_customer) {
                            int left_adj = -1, right_adj = -1;
                            if (i > 0 && !isCustomerSelected[tour.customers[i-1]]) {
                                left_adj = tour.customers[i-1];
                            }
                            if (i < tour.customers.size() - 1 && !isCustomerSelected[tour.customers[i+1]]) {
                                right_adj = tour.customers[i+1];
                            }
                            
                            int customer_to_add = -1;
                            if (left_adj != -1 && right_adj != -1) {
                                customer_to_add = (getRandomFractionFast() < 0.5f) ? left_adj : right_adj;
                            } else if (left_adj != -1) {
                                customer_to_add = left_adj;
                            } else if (right_adj != -1) {
                                customer_to_add = right_adj;
                            }

                            if (customer_to_add != -1) {
                                selectedCustomersList.push_back(customer_to_add);
                                isCustomerSelected[customer_to_add] = 1;
                                added_customer_in_this_attempt = true;
                                break;
                            }
                        }
                    }
                }
                
                if (!added_customer_in_this_attempt && getRandomFractionFast() < LLM_SELECT_PROB_PICK_ANY_FROM_TOUR_IF_ADJ_FAILS) {
                    for(int i = 0; i < LLM_SELECT_FALLBACK_RANDOM_ATTEMPTS; ++i) {
                        int potential_neighbor_in_tour = tour.customers[getRandomNumber(0, (int)tour.customers.size() - 1)];
                        if (potential_neighbor_in_tour != source_customer && 
                            potential_neighbor_in_tour > 0 && potential_neighbor_in_tour <= sol.instance.numCustomers &&
                            isCustomerSelected[potential_neighbor_in_tour] == 0) {
                            selectedCustomersList.push_back(potential_neighbor_in_tour);
                            isCustomerSelected[potential_neighbor_in_tour] = 1;
                            added_customer_in_this_attempt = true;
                            break;
                        }
                    }
                }
            }
        }

        if (!added_customer_in_this_attempt) {
            const auto& neighbors = sol.instance.adj[source_customer];
            if (!neighbors.empty()) {
                potentialNeighborsWithDist.clear();
                int count = 0;
                for (int neighbor_id : neighbors) {
                    if (count >= LLM_SELECT_NUM_SPATIAL_NEIGHBORS_TO_CONSIDER) break;
                    if (neighbor_id > 0 && neighbor_id <= sol.instance.numCustomers && isCustomerSelected[neighbor_id] == 0) {
                        potentialNeighborsWithDist.push_back({sol.instance.distanceMatrix[source_customer][neighbor_id], neighbor_id});
                        count++;
                    }
                }
                
                if (!potentialNeighborsWithDist.empty()) {
                    int customer_to_add = -1;
                    if (getRandomFractionFast() < LLM_SELECT_PROB_SPATIAL_RANDOM_POOL_SELECTION) {
                        int pool_size = getRandomNumber(LLM_SELECT_SPATIAL_RANDOM_POOL_SIZE_MIN, LLM_SELECT_SPATIAL_RANDOM_POOL_SIZE_MAX);
                        pool_size = std::min(pool_size, (int)potentialNeighborsWithDist.size());
                        std::partial_sort(potentialNeighborsWithDist.begin(), potentialNeighborsWithDist.begin() + pool_size, potentialNeighborsWithDist.end());
                        customer_to_add = potentialNeighborsWithDist[getRandomNumber(0, pool_size - 1)].second;
                    } else {
                        std::sort(potentialNeighborsWithDist.begin(), potentialNeighborsWithDist.end());
                        int numCandidates = potentialNeighborsWithDist.size();
                        int chosenIdx = static_cast<int>(numCandidates * std::pow(getRandomFractionFast(), LLM_SELECT_SPATIAL_SELECTION_BIAS_POWER));
                        chosenIdx = std::min(chosenIdx, numCandidates - 1);
                        customer_to_add = potentialNeighborsWithDist[chosenIdx].second;
                    }

                    if (customer_to_add != -1 && isCustomerSelected[customer_to_add] == 0) {
                        selectedCustomersList.push_back(customer_to_add);
                        isCustomerSelected[customer_to_add] = 1;
                        added_customer_in_this_attempt = true;
                    }
                }
            }
        }
        
        if (!added_customer_in_this_attempt) {
            int random_new_customer = -1;
            for (int i = 0; i < LLM_SELECT_FALLBACK_RANDOM_ATTEMPTS; ++i) {
                int potential_random_cust = getRandomNumber(1, sol.instance.numCustomers);
                if (isCustomerSelected[potential_random_cust] == 0) {
                    random_new_customer = potential_random_cust;
                    break;
                }
            }
            if (random_new_customer != -1) {
                selectedCustomersList.push_back(random_new_customer);
                isCustomerSelected[random_new_customer] = 1;
                added_customer_in_this_attempt = true;
            }
        }
        current_attempts_overall++;
    }

    int current_customer_id_scan = 1;
    while (selectedCustomersList.size() < static_cast<size_t>(numCustomersToRemove) && current_customer_id_scan <= sol.instance.numCustomers) {
        if (isCustomerSelected[current_customer_id_scan] == 0) {
            selectedCustomersList.push_back(current_customer_id_scan);
            isCustomerSelected[current_customer_id_scan] = 1;
        }
        current_customer_id_scan++;
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    const float LLM_SORT_STRAT_PROB_TW_WIDTH = 0.095f;
    const float LLM_SORT_STRAT_PROB_DIST_FROM_DEPOT = 0.105f;
    const float LLM_SORT_STRAT_PROB_DEMAND = 0.068f;
    const float LLM_SORT_STRAT_PROB_SERVICE_TIME = 0.058f;
    const float LLM_SORT_STRAT_PROB_START_TW = 0.075f;
    const float LLM_SORT_STRAT_PROB_EARLY_START_TW = 0.075f;
    const float LLM_SORT_STRAT_PROB_NUM_NEIGHBORS = 0.048f;
    const float LLM_SORT_STRAT_PROB_COMBINED_METRIC = 0.103f;
    const float LLM_SORT_STRAT_PROB_RANDOM_SHUFFLE = 0.113f;
    const float LLM_SORT_STRAT_PROB_NN_CHAIN = 0.265f;

    const float LLM_SORT_PROB_ASCENDING = 0.545f;
    const float LLM_NN_CHAIN_STOCHASTIC_DIVERSION_PROB = 0.16f;
    const float LLM_SORT_NN_TIE_BREAK_PROB = 0.45f;
    const float LLM_SORT_EARLY_START_TW_FACTOR = 0.59f;
    const float LLM_SORT_EPSILON = 1e-5f;
    const float LLM_SORT_DEFAULT_START_TW_SCORE = 0.6f;

    const float LLM_SORT_COMB_WEIGHT_TW = 0.18f;
    const float LLM_SORT_COMB_WEIGHT_DEMAND = 0.205f;
    const float LLM_SORT_COMB_WEIGHT_SERVICE = 0.135f;
    const float LLM_SORT_COMB_WEIGHT_DIST = 0.165f;
    const float LLM_SORT_COMB_WEIGHT_START_TW = 0.193f;
    const float LLM_SORT_COMB_WEIGHT_NUM_ADJ = 0.12f;

    const float LLM_SORT_METRIC_NOISE_AMPLITUDE_PCT = 0.00255f;
    const float LLM_SORT_POST_SORT_SWAP_PROB = 0.038f;

    if (customers.empty() || customers.size() == 1) {
        return;
    }

    enum SortStrategy {
        TW_WIDTH,
        DIST_FROM_DEPOT,
        DEMAND,
        SERVICE_TIME,
        START_TW,
        EARLY_START_TW,
        NUM_NEIGHBORS,
        COMBINED_METRIC,
        RANDOM_SHUFFLE,
        NEAREST_NEIGHBOR_CHAIN,
        NUM_STRATEGIES 
    };

    float strategyProbs[NUM_STRATEGIES] = {
        LLM_SORT_STRAT_PROB_TW_WIDTH,
        LLM_SORT_STRAT_PROB_DIST_FROM_DEPOT,
        LLM_SORT_STRAT_PROB_DEMAND,
        LLM_SORT_STRAT_PROB_SERVICE_TIME,
        LLM_SORT_STRAT_PROB_START_TW,
        LLM_SORT_STRAT_PROB_EARLY_START_TW,
        LLM_SORT_STRAT_PROB_NUM_NEIGHBORS,
        LLM_SORT_STRAT_PROB_COMBINED_METRIC,
        LLM_SORT_STRAT_PROB_RANDOM_SHUFFLE,
        LLM_SORT_STRAT_PROB_NN_CHAIN
    };

    float sumProbs = 0.0f;
    for (int i = 0; i < NUM_STRATEGIES; ++i) {
        sumProbs += strategyProbs[i];
    }

    float r_strategy = getRandomFractionFast();
    float cumulativeProb = 0.0f;
    SortStrategy chosenStrategy = RANDOM_SHUFFLE; 
    for (int i = 0; i < NUM_STRATEGIES; ++i) {
        cumulativeProb += strategyProbs[i] / sumProbs; 
        if (r_strategy < cumulativeProb) {
            chosenStrategy = static_cast<SortStrategy>(i);
            break;
        }
    }

    if (chosenStrategy == RANDOM_SHUFFLE) {
        static thread_local std::mt19937 gen_sort_shuffle(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen_sort_shuffle);
        return;
    }

    if (chosenStrategy == NEAREST_NEIGHBOR_CHAIN) {
        std::vector<int> remaining_customers = customers;
        std::vector<int> sorted_customers;
        sorted_customers.reserve(customers.size());

        int current_customer;
        if (!remaining_customers.empty()) {
            int start_idx = getRandomNumber(0, (int)remaining_customers.size() - 1);
            current_customer = remaining_customers[start_idx];
            sorted_customers.push_back(current_customer);
            remaining_customers[start_idx] = remaining_customers.back();
            remaining_customers.pop_back();
        } else {
            return;
        }

        while (!remaining_customers.empty()) {
            int next_customer_to_add = -1;
            int next_customer_idx_in_remaining = -1;

            if (getRandomFractionFast() < LLM_NN_CHAIN_STOCHASTIC_DIVERSION_PROB) {
                next_customer_idx_in_remaining = getRandomNumber(0, (int)remaining_customers.size() - 1);
                next_customer_to_add = remaining_customers[next_customer_idx_in_remaining];
            } else {
                float min_dist = std::numeric_limits<float>::max();
                for (size_t i = 0; i < remaining_customers.size(); ++i) {
                    int customer_id = remaining_customers[i];
                    float dist = instance.distanceMatrix[current_customer][customer_id];
                    if (dist < min_dist) {
                        min_dist = dist;
                        next_customer_to_add = customer_id;
                        next_customer_idx_in_remaining = i;
                    } else if (dist == min_dist && getRandomFractionFast() < LLM_SORT_NN_TIE_BREAK_PROB) {
                         next_customer_to_add = customer_id;
                         next_customer_idx_in_remaining = i;
                    }
                }
            }
            
            if (next_customer_to_add != -1) {
                current_customer = next_customer_to_add;
                sorted_customers.push_back(current_customer);
                remaining_customers[next_customer_idx_in_remaining] = remaining_customers.back();
                remaining_customers.pop_back();
            } else {
                break; 
            }
        }
        customers = sorted_customers;
        return;
    }

    bool ascending = getRandomFractionFast() < LLM_SORT_PROB_ASCENDING;

    std::vector<std::pair<float, int>> customerMetrics;
    customerMetrics.reserve(customers.size());

    float max_tw_width_batch = 0.0f;
    float max_demand_batch = 0.0f;
    float max_service_time_batch = 0.0f;
    float max_dist_depot_batch = 0.0f;
    float max_start_tw_batch = 0.0f;
    float min_start_tw_batch = std::numeric_limits<float>::max();
    float max_num_adj_batch = 0.0f;

    if (chosenStrategy == COMBINED_METRIC) {
        for (int customerId : customers) {
            max_tw_width_batch = std::fmax(max_tw_width_batch, instance.TW_Width[customerId]);
            max_demand_batch = std::fmax(max_demand_batch, static_cast<float>(instance.demand[customerId]));
            max_service_time_batch = std::fmax(max_service_time_batch, instance.serviceTime[customerId]);
            max_dist_depot_batch = std::fmax(max_dist_depot_batch, instance.distanceMatrix[0][customerId]);
            max_start_tw_batch = std::fmax(max_start_tw_batch, instance.startTW[customerId]);
            min_start_tw_batch = std::fmin(min_start_tw_batch, instance.startTW[customerId]);
            max_num_adj_batch = std::fmax(max_num_adj_batch, static_cast<float>(instance.adj[customerId].size()));
        }
    }

    for (int customerId : customers) {
        float metricValue;
        switch (chosenStrategy) {
            case TW_WIDTH: metricValue = instance.TW_Width[customerId]; break;
            case DIST_FROM_DEPOT: metricValue = instance.distanceMatrix[0][customerId]; break;
            case DEMAND: metricValue = static_cast<float>(instance.demand[customerId]); break;
            case SERVICE_TIME: metricValue = instance.serviceTime[customerId]; break;
            case START_TW: metricValue = instance.startTW[customerId]; break;
            case EARLY_START_TW: metricValue = instance.startTW[customerId] + instance.serviceTime[customerId] * LLM_SORT_EARLY_START_TW_FACTOR; break;
            case NUM_NEIGHBORS: metricValue = static_cast<float>(instance.adj[customerId].size()); break;
            case COMBINED_METRIC: {
                float tw_score = (max_tw_width_batch > LLM_SORT_EPSILON) ? (1.0f - (instance.TW_Width[customerId] / max_tw_width_batch)) : 0.0f;
                float demand_score = (max_demand_batch > LLM_SORT_EPSILON) ? (instance.demand[customerId] / max_demand_batch) : 0.0f;
                float service_score = (max_service_time_batch > LLM_SORT_EPSILON) ? (instance.serviceTime[customerId] / max_service_time_batch) : 0.0f;
                float dist_score = (max_dist_depot_batch > LLM_SORT_EPSILON) ? (instance.distanceMatrix[0][customerId] / max_dist_depot_batch) : 0.0f;
                float start_tw_score = 0.0f;
                if (max_start_tw_batch - min_start_tw_batch > LLM_SORT_EPSILON) {
                    start_tw_score = (1.0f - ((instance.startTW[customerId] - min_start_tw_batch) / (max_start_tw_batch - min_start_tw_batch)));
                } else {
                    start_tw_score = LLM_SORT_DEFAULT_START_TW_SCORE;
                }
                float num_adj_score = (max_num_adj_batch > LLM_SORT_EPSILON) ? (static_cast<float>(instance.adj[customerId].size()) / max_num_adj_batch) : 0.0f;
                
                metricValue = (tw_score * LLM_SORT_COMB_WEIGHT_TW) + (demand_score * LLM_SORT_COMB_WEIGHT_DEMAND) + 
                              (service_score * LLM_SORT_COMB_WEIGHT_SERVICE) + (dist_score * LLM_SORT_COMB_WEIGHT_DIST) + 
                              (start_tw_score * LLM_SORT_COMB_WEIGHT_START_TW) + (num_adj_score * LLM_SORT_COMB_WEIGHT_NUM_ADJ);
                break;
            }
            default: metricValue = 0.0f; break;
        }
        customerMetrics.push_back({metricValue, customerId});
    }

    float minAttrVal = std::numeric_limits<float>::max();
    float maxAttrVal = std::numeric_limits<float>::lowest();
    if (!customerMetrics.empty()) {
        minAttrVal = customerMetrics[0].first;
        maxAttrVal = customerMetrics[0].first;
        for (const auto& entry : customerMetrics) {
            if (entry.first < minAttrVal) minAttrVal = entry.first;
            if (entry.first > maxAttrVal) maxAttrVal = entry.first;
        }
    }
    
    float attributeRange = maxAttrVal - minAttrVal;
    if (std::abs(attributeRange) < LLM_SORT_EPSILON) { attributeRange = 1.0f; }
    float perturbationMagnitude = attributeRange * LLM_SORT_METRIC_NOISE_AMPLITUDE_PCT;

    for (auto& entry : customerMetrics) {
        entry.first += (getRandomFractionFast() - 0.5f) * 2.0f * perturbationMagnitude;
    }

    std::sort(customerMetrics.begin(), customerMetrics.end(), [&](const auto& a, const auto& b) {
        if (ascending) {
            return a.first < b.first;
        } else {
            return a.first > b.first;
        }
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerMetrics[i].second;
    }

    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFractionFast() < LLM_SORT_POST_SORT_SWAP_PROB) {
            std::swap(customers[i], customers[i + 1]);
        }
    }
}