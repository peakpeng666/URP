#include <vector>
#include <unordered_set>
#include <algorithm>
#include <utility>
#include <random>
#include <cmath>
#include <numeric>

#include "Solution.h"
#include "Instance.h"
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomersToRemove = getRandomNumber(8, 18);

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    selectedCustomersList.reserve(numCustomersToRemove);

    const float p_initial_segment_removal = getRandomFraction(0.3f, 0.4f);
    const float p_expand_from_existing = getRandomFraction(0.80f, 0.85f);
    const float p_spatial_neighbor_bias = getRandomFraction(0.60f, 0.70f);
    const float probToAddAnyTourCustomer = 0.15f;
    const float SAME_TOUR_CANDIDATE_PREFERENCE_FACTOR = getRandomFraction(0.75f, 0.90f);
    const int max_neighbors_to_evaluate = getRandomNumber(8, 12);
    const int max_selection_pool_size = 5;
    const int maxFailedExpansionAttempts = 10;
    const float p_global_explore_jump = 0.04f;
    const int MAX_GLOBAL_RANDOM_ATTEMPTS = sol.instance.numCustomers * 2;
    const int MAX_TOUR_ATTEMPTS_FOR_SEGMENT = getRandomNumber(3, 5);

    int failedExpansionAttempts = 0;

    if (getRandomFractionFast() < p_initial_segment_removal && !sol.tours.empty()) {
        for (int attempt = 0; attempt < MAX_TOUR_ATTEMPTS_FOR_SEGMENT; ++attempt) {
            int randomTourIdx = getRandomNumber(0, static_cast<int>(sol.tours.size()) - 1);
            const Tour& selectedTour = sol.tours[randomTourIdx];

            if (selectedTour.customers.size() >= 2) {
                int segmentLength = getRandomNumber(2, 5);
                segmentLength = std::min({segmentLength, numCustomersToRemove, static_cast<int>(selectedTour.customers.size())});

                if (segmentLength > 0) {
                    int startPosInTour = 0;
                    if (selectedTour.customers.size() > static_cast<size_t>(segmentLength)) {
                        startPosInTour = getRandomNumber(0, static_cast<int>(selectedTour.customers.size()) - segmentLength);
                    }
                    
                    for (int i = 0; i < segmentLength; ++i) {
                        int customerId = selectedTour.customers[(startPosInTour + i) % selectedTour.customers.size()];
                        if (customerId != 0 && selectedCustomersSet.find(customerId) == selectedCustomersSet.end()) {
                            selectedCustomersSet.insert(customerId);
                            selectedCustomersList.push_back(customerId);
                        }
                    }
                    if (!selectedCustomersList.empty()) {
                        break;
                    }
                }
            }
        }
    }

    if (selectedCustomersList.empty()) {
        int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomersSet.insert(initialCustomer);
        selectedCustomersList.push_back(initialCustomer);
    }
    
    while (selectedCustomersList.size() < static_cast<size_t>(numCustomersToRemove)) {
        int nextCustomerToAdd = -1;
        bool foundLocalCandidate = false;

        if (getRandomFractionFast() < p_expand_from_existing && !selectedCustomersList.empty() && failedExpansionAttempts < maxFailedExpansionAttempts) {
            int pivotCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)]; 

            std::vector<std::pair<float, int>> candidatesWithScores;

            if (pivotCustomer > 0 && pivotCustomer <= sol.instance.numCustomers) {
                if (getRandomFractionFast() < p_spatial_neighbor_bias) { 
                    const auto& neighbors = sol.instance.adj[pivotCustomer];
                    int neighborsConsideredCount = 0;
                    
                    for (int neighbor : neighbors) {
                        if (neighborsConsideredCount >= max_neighbors_to_evaluate) break; 
                        if (neighbor >= 1 && neighbor <= sol.instance.numCustomers && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                            float score = sol.instance.distanceMatrix[pivotCustomer][neighbor];
                            if (sol.customerToTourMap[pivotCustomer] != -1 && sol.customerToTourMap[neighbor] != -1 && 
                                sol.customerToTourMap[pivotCustomer] == sol.customerToTourMap[neighbor]) { 
                                score *= SAME_TOUR_CANDIDATE_PREFERENCE_FACTOR;
                            }
                            candidatesWithScores.push_back({score, neighbor});
                        }
                        neighborsConsideredCount++;
                    }

                    if (!candidatesWithScores.empty()) {
                        std::sort(candidatesWithScores.begin(), candidatesWithScores.end()); 
                        int numPool = std::min(max_selection_pool_size, static_cast<int>(candidatesWithScores.size()));
                        int selectedIdxInPool = 0;
                        if (numPool > 1) { 
                            selectedIdxInPool = static_cast<int>(numPool * std::pow(getRandomFractionFast(), 2.0f)); 
                            selectedIdxInPool = std::min(selectedIdxInPool, numPool - 1);
                        }
                        nextCustomerToAdd = candidatesWithScores[selectedIdxInPool].second;
                        foundLocalCandidate = true;
                    }

                } else { 
                    int tourIdx = sol.customerToTourMap[pivotCustomer];
                    if (tourIdx != -1 && tourIdx < static_cast<int>(sol.tours.size())) {
                        const Tour& currentTour = sol.tours[tourIdx];
                        auto it = std::find(currentTour.customers.begin(), currentTour.customers.end(), pivotCustomer);
                        if (it != currentTour.customers.end()) {
                            int pivotPos = static_cast<int>(std::distance(currentTour.customers.begin(), it));
                            
                            if (currentTour.customers.size() > 1) { 
                                int nextCustomerInTour = currentTour.customers[(pivotPos + 1) % currentTour.customers.size()];
                                if (nextCustomerInTour != 0 && selectedCustomersSet.find(nextCustomerInTour) == selectedCustomersSet.end()) { 
                                    candidatesWithScores.push_back({0.0f, nextCustomerInTour});
                                }
                                int prevCustomerInTour = currentTour.customers[(pivotPos - 1 + currentTour.customers.size()) % currentTour.customers.size()];
                                if (prevCustomerInTour != 0 && selectedCustomersSet.find(prevCustomerInTour) == selectedCustomersSet.end()) { 
                                    candidatesWithScores.push_back({0.0f, prevCustomerInTour});
                                }
                            }
                            
                            if (currentTour.customers.size() > 2 && getRandomFractionFast() < probToAddAnyTourCustomer) {
                                int randomTourCustomerIdx = getRandomNumber(0, static_cast<int>(currentTour.customers.size()) - 1);
                                int randomTourCustomer = currentTour.customers[randomTourCustomerIdx];
                                if (randomTourCustomer != 0 && selectedCustomersSet.find(randomTourCustomer) == selectedCustomersSet.end()) {
                                    candidatesWithScores.push_back({0.0f, randomTourCustomer});
                                }
                            }
                        }
                    }

                    if (!candidatesWithScores.empty()) {
                        nextCustomerToAdd = candidatesWithScores[getRandomNumber(0, static_cast<int>(candidatesWithScores.size()) - 1)].second;
                        foundLocalCandidate = true;
                    }
                }
            }
        }

        if (foundLocalCandidate && selectedCustomersSet.find(nextCustomerToAdd) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(nextCustomerToAdd);
            selectedCustomersList.push_back(nextCustomerToAdd);
            failedExpansionAttempts = 0; 
        } else { 
            failedExpansionAttempts++;
            if (failedExpansionAttempts > maxFailedExpansionAttempts || getRandomFractionFast() < p_global_explore_jump || selectedCustomersList.empty()) { 
                int attempts = 0;
                nextCustomerToAdd = -1; 
                do {
                    nextCustomerToAdd = getRandomNumber(1, sol.instance.numCustomers);
                    attempts++;
                    if (attempts > MAX_GLOBAL_RANDOM_ATTEMPTS) {
                        nextCustomerToAdd = -1; 
                        break;
                    }
                } while (selectedCustomersSet.count(nextCustomerToAdd) > 0);
            
                if (nextCustomerToAdd != -1) {
                    selectedCustomersSet.insert(nextCustomerToAdd);
                    selectedCustomersList.push_back(nextCustomerToAdd);
                    failedExpansionAttempts = 0; 
                } else {
                    break; 
                }
            }
        }
    }
    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    if (getRandomFractionFast() < 0.06f) { 
        static thread_local std::mt19937 gen(std::random_device{}()); 
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    enum SortStrategy {
        TW_WIDTH_ASC,
        START_TW_ASC,
        DEMAND_DESC,
        SERVICE_TIME_DESC,
        DIST_TO_DEPOT_DESC,
        COMPOSITE_CRITICALITY,
        COMPOSITE_SPATIAL,
        COMPOSITE_DYNAMIC
    };

    float r = getRandomFractionFast(); 
    SortStrategy chosenStrategy;

    if (r < 0.12f) { 
        chosenStrategy = TW_WIDTH_ASC;
    } else if (r < 0.24f) { 
        chosenStrategy = START_TW_ASC;
    } else if (r < 0.34f) { 
        chosenStrategy = DEMAND_DESC;
    } else if (r < 0.42f) { 
        chosenStrategy = SERVICE_TIME_DESC;
    } else if (r < 0.55f) { 
        chosenStrategy = DIST_TO_DEPOT_DESC;
    } else if (r < 0.70f) { 
        chosenStrategy = COMPOSITE_CRITICALITY;
    } else if (r < 0.85f) { 
        chosenStrategy = COMPOSITE_SPATIAL;
    } else { 
        chosenStrategy = COMPOSITE_DYNAMIC;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    const float EPSILON_PERTURBATION_FACTOR = 1e-4f; 

    float rand_mult_tw_width = 0.5f + getRandomFractionFast() * 1.5f; 
    float rand_mult_start_tw = 0.5f + getRandomFractionFast() * 1.5f;
    float rand_mult_service_time = 0.5f + getRandomFractionFast() * 1.5f;
    float rand_mult_demand = 0.5f + getRandomFractionFast() * 1.5f;
    float rand_mult_dist_depot = 0.5f + getRandomFractionFast() * 1.5f;
    float rand_mult_inverse_tw_tightness = getRandomFraction(0.01f, 1.0f);

    for (int customerIdx : customers) {
        float score = 0.0f;

        switch (chosenStrategy) {
            case TW_WIDTH_ASC:
                score = instance.TW_Width[customerIdx];
                break;
            case START_TW_ASC: 
                score = instance.startTW[customerIdx];
                break;
            case DEMAND_DESC:
                score = -static_cast<float>(instance.demand[customerIdx]);
                break;
            case SERVICE_TIME_DESC: 
                score = -instance.serviceTime[customerIdx];
                break;
            case DIST_TO_DEPOT_DESC:
                score = -instance.distanceMatrix[0][customerIdx];
                break;
            case COMPOSITE_CRITICALITY:
                {
                    const float CRITICALITY_PERTURB_RANGE = 0.1f;
                    float critical_tw_width_weight = 1.0f + (getRandomFractionFast() - 0.5f) * CRITICALITY_PERTURB_RANGE;
                    float critical_service_time_weight = 0.5f + (getRandomFractionFast() - 0.5f) * CRITICALITY_PERTURB_RANGE;
                    float critical_demand_weight = 0.05f + (getRandomFractionFast() - 0.5f) * CRITICALITY_PERTURB_RANGE;

                    score = instance.TW_Width[customerIdx] * critical_tw_width_weight
                            + instance.serviceTime[customerIdx] * critical_service_time_weight
                            - static_cast<float>(instance.demand[customerIdx]) * critical_demand_weight;
                }
                break;
            case COMPOSITE_SPATIAL:
                {
                    float w_dist = getRandomFraction(0.5f, 1.5f);
                    float w_start_tw = getRandomFraction(0.05f, 0.2f);
                    float w_demand_spatial = getRandomFraction(0.01f, 0.05f);

                    float composite_spatial_val = instance.distanceMatrix[0][customerIdx] * w_dist
                                                  + instance.startTW[customerIdx] * w_start_tw
                                                  - static_cast<float>(instance.demand[customerIdx]) * w_demand_spatial;
                    if (getRandomFractionFast() < 0.15f) { 
                        score = -composite_spatial_val;
                    } else {
                        score = composite_spatial_val;
                    }
                }
                break;
            case COMPOSITE_DYNAMIC:
                {
                    float base_weight_inv_tw_width = 1.0f; 
                    float base_weight_demand = 0.015f;
                    float base_weight_service_time = 0.2f;
                    float base_weight_start_tw = 1.0f;
                    float base_weight_dist_to_depot = 0.05f;

                    float composite_score_val = 0.0f;
                    if (instance.TW_Width[customerIdx] > 0.001f) { 
                        composite_score_val += (base_weight_inv_tw_width / instance.TW_Width[customerIdx]) * rand_mult_tw_width;
                        composite_score_val += (rand_mult_inverse_tw_tightness / instance.TW_Width[customerIdx]);
                    } else {
                        composite_score_val += (base_weight_inv_tw_width * 10000.0f) * rand_mult_tw_width; 
                        composite_score_val += (rand_mult_inverse_tw_tightness * 10000.0f);
                    }
                    composite_score_val += static_cast<float>(instance.demand[customerIdx]) * base_weight_demand * rand_mult_demand;
                    composite_score_val += instance.serviceTime[customerIdx] * base_weight_service_time * rand_mult_service_time;
                    composite_score_val += instance.startTW[customerIdx] * base_weight_start_tw * rand_mult_start_tw;
                    composite_score_val += instance.distanceMatrix[0][customerIdx] * base_weight_dist_to_depot * rand_mult_dist_depot;
                    
                    bool composite_reverse_sign = getRandomFractionFast() < 0.30f;
                    score = composite_reverse_sign ? composite_score_val : -composite_score_val;
                }
                break;
        }
        
        score += getRandomFractionFast() * EPSILON_PERTURBATION_FACTOR; 
        customerScores.push_back({score, customerIdx});
    }

    std::sort(customerScores.begin(), customerScores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }

    if (customers.size() > 1) {
        float p_swap_perturb_adj = 0.15f;
        for (size_t i = 0; i < customers.size() - 1; ++i) {
            if (getRandomFractionFast() < p_swap_perturb_adj) {
                std::swap(customers[i], customers[i+1]);
            }
        }
    }
    
    float p_broad_random_swaps = 0.10f; 
    if (getRandomFractionFast() < p_broad_random_swaps) {
        int num_random_swaps = getRandomNumber(0, std::min(static_cast<int>(customers.size() / 4), 3));
        for (int k = 0; k < num_random_swaps; ++k) {
            int idx1 = getRandomNumber(0, customers.size() - 1);
            int idx2 = getRandomNumber(0, customers.size() - 1);
            if (idx1 != idx2) {
                std::swap(customers[idx1], customers[idx2]);
            }
        }
    }
}