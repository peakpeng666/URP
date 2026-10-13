#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <numeric>
#include <limits>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int SELECT_NUM_CUSTOMERS_TO_REMOVE_MIN = 8;
    const int SELECT_NUM_CUSTOMERS_TO_REMOVE_MAX = 18;
    const int SELECT_NUM_ADJ_TO_CONSIDER_MIN = 4;
    const int SELECT_NUM_ADJ_TO_CONSIDER_MAX = 10;
    const float SELECT_SAME_TOUR_OTHER_CUSTOMER_ADD_PROB = 0.7f;
    const float SELECT_EXPLORATION_PROB = 0.05f; 
    const int SELECT_MAX_ITER_NO_PROGRESS_FALLBACK = 5;

    std::vector<char> is_customer_selected(sol.instance.numCustomers + 1, 0); 
    std::vector<int> selectedCustomersVec; 
    const Instance& instance = sol.instance;

    int numCustomersToRemove = getRandomNumber(SELECT_NUM_CUSTOMERS_TO_REMOVE_MIN, std::min(SELECT_NUM_CUSTOMERS_TO_REMOVE_MAX, instance.numCustomers));

    if (numCustomersToRemove == 0 || instance.numCustomers == 0) {
        return {};
    }

    selectedCustomersVec.reserve(numCustomersToRemove); 

    int seed_customer = getRandomNumber(1, instance.numCustomers);
    is_customer_selected[seed_customer] = 1;
    selectedCustomersVec.push_back(seed_customer);

    int iterations_without_progress = 0;

    while (selectedCustomersVec.size() < static_cast<size_t>(numCustomersToRemove)) {
        std::vector<int> potentialNewCustomers;
        potentialNewCustomers.reserve(SELECT_NUM_ADJ_TO_CONSIDER_MAX * 2 + 10); 

        if (!selectedCustomersVec.empty()) {
            int source_idx = getRandomNumber(0, static_cast<int>(selectedCustomersVec.size()) - 1);
            int source_customer = selectedCustomersVec[source_idx];

            int num_adj_to_consider_actual = getRandomNumber(SELECT_NUM_ADJ_TO_CONSIDER_MIN, SELECT_NUM_ADJ_TO_CONSIDER_MAX);
            int neighbors_added_count = 0;
            if (source_customer >= 1 && source_customer <= instance.numCustomers) {
                for (int neighbor_customer : instance.adj[source_customer]) {
                    if (neighbor_customer > 0 && neighbor_customer <= instance.numCustomers && is_customer_selected[neighbor_customer] == 0) {
                        potentialNewCustomers.push_back(neighbor_customer);
                        neighbors_added_count++;
                        if (neighbors_added_count >= num_adj_to_consider_actual) {
                            break; 
                        }
                    }
                }
            }
            
            int tour_idx = sol.customerToTourMap[source_customer];
            if (tour_idx != -1 && tour_idx < static_cast<int>(sol.tours.size())) {
                const Tour& currentTour = sol.tours[tour_idx];
                if (!currentTour.customers.empty()) {
                    auto it = std::find(currentTour.customers.begin(), currentTour.customers.end(), source_customer);
                    if (it != currentTour.customers.end()) {
                        int pos = std::distance(currentTour.customers.begin(), it);
                        int tourSize = static_cast<int>(currentTour.customers.size());
                        
                        if (tourSize > 1) { 
                            int nextInTour = currentTour.customers[(pos + 1) % tourSize];
                            int prevInTour = currentTour.customers[(pos - 1 + tourSize) % tourSize]; 

                            if (nextInTour > 0 && nextInTour <= instance.numCustomers && nextInTour != source_customer && is_customer_selected[nextInTour] == 0) {
                                potentialNewCustomers.push_back(nextInTour);
                            }
                            if (prevInTour > 0 && prevInTour <= instance.numCustomers && prevInTour != source_customer && is_customer_selected[prevInTour] == 0) {
                                potentialNewCustomers.push_back(prevInTour);
                            }
                        }
                        
                        for (int cust_on_tour : currentTour.customers) {
                            if (cust_on_tour != source_customer && cust_on_tour > 0 && cust_on_tour <= instance.numCustomers && is_customer_selected[cust_on_tour] == 0) {
                                if (getRandomFractionFast() < SELECT_SAME_TOUR_OTHER_CUSTOMER_ADD_PROB) {
                                    potentialNewCustomers.push_back(cust_on_tour);
                                }
                            }
                        }
                    }
                }
            }
        }

        if (getRandomFractionFast() < SELECT_EXPLORATION_PROB) {
            int random_unselected_customer;
            int attempts_exploration = 0;
            do {
                random_unselected_customer = getRandomNumber(1, instance.numCustomers);
                attempts_exploration++;
                if (attempts_exploration > instance.numCustomers * 2) break; 
            } while (is_customer_selected[random_unselected_customer] == 1);

            if (is_customer_selected[random_unselected_customer] == 0 && attempts_exploration <= instance.numCustomers * 2) {
                 potentialNewCustomers.push_back(random_unselected_customer);
            }
        }
        
        int chosen_customer = -1;
        if (potentialNewCustomers.empty() || iterations_without_progress >= SELECT_MAX_ITER_NO_PROGRESS_FALLBACK) {
            int new_random_customer;
            int attempts = 0;
            do {
                new_random_customer = getRandomNumber(1, instance.numCustomers);
                attempts++;
                if (attempts > instance.numCustomers * 2) { 
                    break;
                }
            } while (is_customer_selected[new_random_customer] == 1);
            
            if (is_customer_selected[new_random_customer] == 0) {
                chosen_customer = new_random_customer;
            }
        } else {
            int selected_candidate_idx = getRandomNumber(0, static_cast<int>(potentialNewCustomers.size()) - 1);
            chosen_customer = potentialNewCustomers[selected_candidate_idx];
            
            if (is_customer_selected[chosen_customer] == 1) {
                chosen_customer = -1; 
            }
        }
        
        if (chosen_customer != -1) {
            is_customer_selected[chosen_customer] = 1;
            selectedCustomersVec.push_back(chosen_customer);
            iterations_without_progress = 0;
        } else {
            iterations_without_progress++;
            if (iterations_without_progress > 2 * SELECT_MAX_ITER_NO_PROGRESS_FALLBACK && selectedCustomersVec.size() > 0) {
                 break;
            }
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    const int SORT_STRATEGY_GROUP_DETERMINISTIC_THRESHOLD = 8; 
    const int SORT_STRATEGY_GROUP_MAX_RANDOM_NUMBER = 9;      
    const float SORT_COMBINED_WEIGHT_MIN = 0.5f;
    const float SORT_COMBINED_WEIGHT_MAX = 1.5f;
    const float SORT_COMBINED_SCORE_NOISE = 0.01f;
    const float SORT_EPSILON_FOR_RANGE = 1e-6f;
    const int SORT_MAX_POST_PROCESS_SWAPS_CAP = 3;

    enum SortStrategy {
        TW_WIDTH_ASC,
        DEMAND_DESC,
        DIST_DEPOT_DESC,
        START_TW_ASC,
        SERVICE_TIME_DESC,
        COMBINED_SCORE_DESC
    };

    if (customers.empty()) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());
    bool apply_post_process_swaps = false;

    int strategy_group_choice = getRandomNumber(0, SORT_STRATEGY_GROUP_MAX_RANDOM_NUMBER); 

    if (strategy_group_choice < SORT_STRATEGY_GROUP_DETERMINISTIC_THRESHOLD) { 
        apply_post_process_swaps = true;
        int specific_strategy_choice = getRandomNumber(0, 5); 

        SortStrategy chosenStrategy;
        if (specific_strategy_choice == 0) chosenStrategy = TW_WIDTH_ASC;
        else if (specific_strategy_choice == 1) chosenStrategy = DEMAND_DESC;
        else if (specific_strategy_choice == 2) chosenStrategy = DIST_DEPOT_DESC;
        else if (specific_strategy_choice == 3) chosenStrategy = START_TW_ASC;
        else if (specific_strategy_choice == 4) chosenStrategy = SERVICE_TIME_DESC;
        else chosenStrategy = COMBINED_SCORE_DESC;

        if (chosenStrategy == TW_WIDTH_ASC) {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.TW_Width[c1] < instance.TW_Width[c2];
            });
        } else if (chosenStrategy == DEMAND_DESC) {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.demand[c1] > instance.demand[c2];
            });
        } else if (chosenStrategy == DIST_DEPOT_DESC) {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.distanceMatrix[0][c1] > instance.distanceMatrix[0][c2];
            });
        } else if (chosenStrategy == START_TW_ASC) {
             std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.startTW[c1] < instance.startTW[c2];
            });
        } else if (chosenStrategy == SERVICE_TIME_DESC) {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.serviceTime[c1] > instance.serviceTime[c2];
            });
        } else { 
            float max_tw_width = 0.0f, min_tw_width = std::numeric_limits<float>::max();
            float max_demand = 0.0f, min_demand = std::numeric_limits<float>::max();
            float max_service_time = 0.0f, min_service_time = std::numeric_limits<float>::max();
            float max_dist_depot = 0.0f, min_dist_depot = std::numeric_limits<float>::max();
            float max_start_tw = 0.0f, min_start_tw = std::numeric_limits<float>::max();

            for (int cust_id : customers) {
                max_tw_width = std::max(max_tw_width, instance.TW_Width[cust_id]);
                min_tw_width = std::min(min_tw_width, instance.TW_Width[cust_id]);
                max_demand = std::max(max_demand, static_cast<float>(instance.demand[cust_id]));
                min_demand = std::min(min_demand, static_cast<float>(instance.demand[cust_id]));
                max_service_time = std::max(max_service_time, instance.serviceTime[cust_id]);
                min_service_time = std::min(min_service_time, instance.serviceTime[cust_id]);
                max_dist_depot = std::max(max_dist_depot, instance.distanceMatrix[0][cust_id]);
                min_dist_depot = std::min(min_dist_depot, instance.distanceMatrix[0][cust_id]);
                max_start_tw = std::max(max_start_tw, instance.startTW[cust_id]);
                min_start_tw = std::min(min_start_tw, instance.startTW[cust_id]);
            }
            
            float range_tw = (max_tw_width - min_tw_width);
            if (range_tw < SORT_EPSILON_FOR_RANGE) range_tw = 1.0f;

            float range_demand = (max_demand - min_demand);
            if (range_demand < SORT_EPSILON_FOR_RANGE) range_demand = 1.0f;

            float range_service = (max_service_time - min_service_time);
            if (range_service < SORT_EPSILON_FOR_RANGE) range_service = 1.0f;

            float range_dist = (max_dist_depot - min_dist_depot);
            if (range_dist < SORT_EPSILON_FOR_RANGE) range_dist = 1.0f;

            float range_start_tw = (max_start_tw - min_start_tw);
            if (range_start_tw < SORT_EPSILON_FOR_RANGE) range_start_tw = 1.0f;

            float w_tw = getRandomFraction(SORT_COMBINED_WEIGHT_MIN, SORT_COMBINED_WEIGHT_MAX);
            float w_demand = getRandomFraction(SORT_COMBINED_WEIGHT_MIN, SORT_COMBINED_WEIGHT_MAX);
            float w_service = getRandomFraction(SORT_COMBINED_WEIGHT_MIN, SORT_COMBINED_WEIGHT_MAX);
            float w_dist_depot = getRandomFraction(SORT_COMBINED_WEIGHT_MIN, SORT_COMBINED_WEIGHT_MAX);
            float w_start_tw = getRandomFraction(SORT_COMBINED_WEIGHT_MIN, SORT_COMBINED_WEIGHT_MAX);

            float sum_weights = w_tw + w_demand + w_service + w_dist_depot + w_start_tw;
            if (sum_weights > SORT_EPSILON_FOR_RANGE) { 
                w_tw /= sum_weights;
                w_demand /= sum_weights;
                w_service /= sum_weights;
                w_dist_depot /= sum_weights;
                w_start_tw /= sum_weights;
            } else { 
                w_tw = w_demand = w_service = w_dist_depot = w_start_tw = 0.2f; 
            }

            std::vector<std::pair<float, int>> customerScores;
            customerScores.reserve(customers.size());

            for (int customerId : customers) {
                float score = 0.0f;
                score += w_tw * ((max_tw_width - instance.TW_Width[customerId]) / range_tw); 
                score += w_demand * ((static_cast<float>(instance.demand[customerId]) - min_demand) / range_demand);
                score += w_service * ((instance.serviceTime[customerId] - min_service_time) / range_service);
                score += w_dist_depot * ((static_cast<float>(instance.distanceMatrix[0][customerId]) - min_dist_depot) / range_dist);
                score += w_start_tw * ((max_start_tw - instance.startTW[customerId]) / range_start_tw); 
                
                score += getRandomFraction(-SORT_COMBINED_SCORE_NOISE, SORT_COMBINED_SCORE_NOISE); 
                
                customerScores.push_back({score, customerId});
            }
            
            std::sort(customerScores.rbegin(), customerScores.rend()); 
            
            for (size_t i = 0; i < customers.size(); ++i) {
                customers[i] = customerScores[i].second;
            }
        }
    } else { 
        std::shuffle(customers.begin(), customers.end(), gen);
    }

    if (apply_post_process_swaps) { 
        int num_swaps = getRandomNumber(0, std::min(static_cast<int>(customers.size() / 3), SORT_MAX_POST_PROCESS_SWAPS_CAP));
        for (int i = 0; i < num_swaps; ++i) {
            if (customers.size() > 1) {
                int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 2);
                std::swap(customers[idx1], customers[idx1 + 1]); 
            }
        }
    }
}