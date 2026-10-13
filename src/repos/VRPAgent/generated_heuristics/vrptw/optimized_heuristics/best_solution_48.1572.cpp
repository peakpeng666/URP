#include <random>
#include <vector>
#include <algorithm>
#include <utility>
#include <numeric>
#include <cmath>
#include <limits>

#include "Utils.h"
#include "Solution.h"
#include "Instance.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const float MIN_REMOVAL_PERCENTAGE = 0.01F;
    const float MAX_REMOVAL_PERCENTAGE = 0.03F;
    const int MIN_ABSOLUTE_REMOVAL = 7;
    const int MAX_ABSOLUTE_REMOVAL = 25;
    const int PROXIMITY_ATTEMPTS_MULTIPLIER = 6;
    const int MIN_SPATIAL_NEIGHBORS_TO_CHECK = 5;
    const int MAX_SPATIAL_NEIGHBORS_TO_CHECK = 18;
    const float TOUR_PROXIMITY_WEIGHT = 0.60F;
    const float ADJACENT_TOUR_CUSTOMER_WEIGHT = 0.80F;
    const float SPATIAL_PICK_BIAS_EXPONENT = 1.8F;

    std::vector<char> isCustomerSelected(sol.instance.numCustomers + 1, 0);
    std::vector<int> selectedCustomersResult;
    std::vector<int> anchorCustomers;

    int numCustomers = sol.instance.numCustomers;
    int min_removal = std::max(MIN_ABSOLUTE_REMOVAL, (int)(MIN_REMOVAL_PERCENTAGE * numCustomers));
    int max_removal = std::min(MAX_ABSOLUTE_REMOVAL, (int)(MAX_REMOVAL_PERCENTAGE * numCustomers));
    int numCustomersToRemove = getRandomNumber(min_removal, max_removal);
    numCustomersToRemove = std::min(numCustomersToRemove, numCustomers);

    int initialSeedCustomer = -1;
    if (!sol.tours.empty()) {
        std::vector<int> candidate_tour_indices;
        for (size_t i = 0; i < sol.tours.size(); ++i) {
            bool has_actual_customers = false;
            for (int cust_id : sol.tours[i].customers) {
                if (cust_id != 0) {
                    has_actual_customers = true;
                    break;
                }
            }
            if (has_actual_customers) {
                candidate_tour_indices.push_back(i);
            }
        }

        if (!candidate_tour_indices.empty()) {
            int random_tour_idx = candidate_tour_indices[getRandomNumber(0, candidate_tour_indices.size() - 1)];
            const auto& tour_customers = sol.tours[random_tour_idx].customers;
            
            std::vector<int> actual_customers_in_tour;
            for (int customer_id_in_tour : tour_customers) {
                if (customer_id_in_tour != 0) {
                    actual_customers_in_tour.push_back(customer_id_in_tour);
                }
            }

            if (!actual_customers_in_tour.empty()) {
                initialSeedCustomer = actual_customers_in_tour[getRandomNumber(0, actual_customers_in_tour.size() - 1)];
            }
        }
    }
    
    if (initialSeedCustomer == -1 || initialSeedCustomer == 0) { 
        initialSeedCustomer = getRandomNumber(1, numCustomers);
    }
    
    if (isCustomerSelected[initialSeedCustomer] == 0) {
        isCustomerSelected[initialSeedCustomer] = 1;
        selectedCustomersResult.push_back(initialSeedCustomer);
        anchorCustomers.push_back(initialSeedCustomer);
    }

    int maxProximityAttempts = numCustomersToRemove * PROXIMITY_ATTEMPTS_MULTIPLIER;
    int currentProximityAttempts = 0;

    std::vector<int> tourCandidates;
    std::vector<int> anyTourCustomers;
    std::vector<std::pair<float, int>> potential_spatial_customers_dist;
    potential_spatial_customers_dist.reserve(MAX_SPATIAL_NEIGHBORS_TO_CHECK);
    
    while (selectedCustomersResult.size() < numCustomersToRemove) {
        bool customerAddedInThisIteration = false;

        if (currentProximityAttempts >= maxProximityAttempts || anchorCustomers.empty()) {
            int candidateCustomer = getRandomNumber(1, numCustomers);
            if (isCustomerSelected[candidateCustomer] == 0) {
                isCustomerSelected[candidateCustomer] = 1;
                selectedCustomersResult.push_back(candidateCustomer);
                anchorCustomers.push_back(candidateCustomer);
                customerAddedInThisIteration = true;
            }
            currentProximityAttempts = 0;
        } else {
            int anchorIdx = getRandomNumber(0, anchorCustomers.size() - 1);
            int anchorCustomerId = anchorCustomers[anchorIdx];

            float proximityTypeRand = getRandomFraction();

            if (proximityTypeRand < TOUR_PROXIMITY_WEIGHT) {
                int tourIdx = sol.customerToTourMap[anchorCustomerId];
                if (tourIdx >= 0 && tourIdx < sol.tours.size()) {
                    const auto& tourCustomers = sol.tours[tourIdx].customers;
                    
                    tourCandidates.clear();
                    int currentSeedInTourIdx = -1;
                    for (size_t i = 0; i < tourCustomers.size(); ++i) {
                        if (tourCustomers[i] == anchorCustomerId) {
                            currentSeedInTourIdx = i;
                            break;
                        }
                    }

                    if (currentSeedInTourIdx != -1) {
                        if (currentSeedInTourIdx > 0 && tourCustomers[currentSeedInTourIdx - 1] != 0 && isCustomerSelected[tourCustomers[currentSeedInTourIdx - 1]] == 0) {
                            tourCandidates.push_back(tourCustomers[currentSeedInTourIdx - 1]);
                        }
                        if (currentSeedInTourIdx < tourCustomers.size() - 1 && tourCustomers[currentSeedInTourIdx + 1] != 0 && isCustomerSelected[tourCustomers[currentSeedInTourIdx + 1]] == 0) {
                            tourCandidates.push_back(tourCustomers[currentSeedInTourIdx + 1]);
                        }
                    }

                    if (!tourCandidates.empty() && getRandomFraction() < ADJACENT_TOUR_CUSTOMER_WEIGHT) {
                        int chosenCustomer = tourCandidates[getRandomNumber(0, tourCandidates.size() - 1)];
                        isCustomerSelected[chosenCustomer] = 1;
                        selectedCustomersResult.push_back(chosenCustomer);
                        anchorCustomers.push_back(chosenCustomer);
                        customerAddedInThisIteration = true;
                        currentProximityAttempts = 0;
                    } else {
                        anyTourCustomers.clear();
                        for (int c : tourCustomers) {
                            if (c != 0 && isCustomerSelected[c] == 0) {
                                anyTourCustomers.push_back(c);
                            }
                        }
                        if (!anyTourCustomers.empty()) {
                            int chosenCustomer = anyTourCustomers[getRandomNumber(0, anyTourCustomers.size() - 1)];
                            isCustomerSelected[chosenCustomer] = 1;
                            selectedCustomersResult.push_back(chosenCustomer);
                            anchorCustomers.push_back(chosenCustomer);
                            customerAddedInThisIteration = true;
                            currentProximityAttempts = 0;
                        }
                    }
                }
            } else {
                const auto& neighbors = sol.instance.adj[anchorCustomerId];
                int searchLimit = std::min((int)neighbors.size(), getRandomNumber(MIN_SPATIAL_NEIGHBORS_TO_CHECK, MAX_SPATIAL_NEIGHBORS_TO_CHECK));

                potential_spatial_customers_dist.clear();
                for (int i = 0; i < searchLimit; ++i) {
                    int neighborId = neighbors[i];
                    if (neighborId != 0 && isCustomerSelected[neighborId] == 0) {
                        potential_spatial_customers_dist.push_back({sol.instance.distanceMatrix[anchorCustomerId][neighborId], neighborId});
                    }
                }
                
                if (!potential_spatial_customers_dist.empty()) {
                    std::sort(potential_spatial_customers_dist.begin(), potential_spatial_customers_dist.end());
                    
                    int pickIndex = static_cast<int>(std::floor(std::pow(getRandomFraction(), SPATIAL_PICK_BIAS_EXPONENT) * potential_spatial_customers_dist.size()));
                    pickIndex = std::min(pickIndex, (int)potential_spatial_customers_dist.size() - 1);
                    int chosenCustomer = potential_spatial_customers_dist[pickIndex].second;
                    
                    isCustomerSelected[chosenCustomer] = 1;
                    selectedCustomersResult.push_back(chosenCustomer);
                    anchorCustomers.push_back(chosenCustomer);
                    customerAddedInThisIteration = true;
                    currentProximityAttempts = 0;
                }
            }
        }
        
        if (!customerAddedInThisIteration) {
            currentProximityAttempts++;
        }
    }

    return selectedCustomersResult;
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const std::vector<float> STRATEGY_WEIGHTS = {
        0.18F,
        0.08F,
        0.08F,
        0.08F,
        0.03F,
        0.18F,
        0.22F,
        0.15F
    };
    const float COMBINED_STRATEGY_RAND_MIN_WEIGHT = 0.3F;
    const float COMBINED_STRATEGY_RAND_RANGE = 0.7F;
    const float PERTURBATION_SCALE = 0.10F;
    const int MAX_POST_SORT_SWAPS = 6;

    static thread_local std::mt19937 gen(std::random_device{}());

    float randVal = getRandomFractionFast();
    int strategyIdx = -1;
    float cumulativeWeight = 0.0F;
    for (size_t i = 0; i < STRATEGY_WEIGHTS.size(); ++i) {
        cumulativeWeight += STRATEGY_WEIGHTS[i];
        if (randVal < cumulativeWeight) {
            strategyIdx = i;
            break;
        }
    }
    if (strategyIdx == -1) strategyIdx = STRATEGY_WEIGHTS.size() - 1;

    if (strategyIdx == 7) {
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customerId : customers) {
        float score = 0.0F;
        switch (strategyIdx) {
            case 0:
                score = 1.0F / (instance.TW_Width[customerId] + 0.01F);
                break;
            case 1:
                score = instance.serviceTime[customerId];
                break;
            case 2:
                score = (float)instance.demand[customerId];
                break;
            case 3:
                score = instance.distanceMatrix[0][customerId];
                break;
            case 4:
                score = -instance.startTW[customerId];
                break;
            case 5:
            {
                float min_dist_to_other_removed = std::numeric_limits<float>::max();
                if (customers.size() > 1) {
                    for (int other_customer_id : customers) {
                        if (customerId == other_customer_id) continue;
                        min_dist_to_other_removed = std::min(min_dist_to_other_removed, instance.distanceMatrix[customerId][other_customer_id]);
                    }
                }
                if (min_dist_to_other_removed == std::numeric_limits<float>::max()) {
                    score = 1.0F / 0.01F;
                } else {
                    score = 1.0F / (min_dist_to_other_removed + 0.01F);
                }
            }
                break;
            case 6:
            {
                float tw_w = getRandomFractionFast() * COMBINED_STRATEGY_RAND_RANGE + COMBINED_STRATEGY_RAND_MIN_WEIGHT;
                float dem_w = getRandomFractionFast() * COMBINED_STRATEGY_RAND_RANGE + COMBINED_STRATEGY_RAND_MIN_WEIGHT;
                float serv_w = getRandomFractionFast() * COMBINED_STRATEGY_RAND_RANGE + COMBINED_STRATEGY_RAND_MIN_WEIGHT;
                float dist_w = getRandomFractionFast() * COMBINED_STRATEGY_RAND_RANGE + COMBINED_STRATEGY_RAND_MIN_WEIGHT;
                float start_tw_w = getRandomFractionFast() * COMBINED_STRATEGY_RAND_RANGE + COMBINED_STRATEGY_RAND_MIN_WEIGHT;

                score = (tw_w / (instance.TW_Width[customerId] + 0.01F)) +
                        (dem_w * instance.demand[customerId]) +
                        (serv_w * instance.serviceTime[customerId]) +
                        (dist_w * instance.distanceMatrix[0][customerId]) +
                        (-start_tw_w * instance.startTW[customerId]);
            }
                break;
            default:
                break;
        }
        
        score *= (1.0F + (getRandomFractionFast() * 2.0F - 1.0F) * PERTURBATION_SCALE);
        scoredCustomers.emplace_back(score, customerId);
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }

    int num_swaps = getRandomNumber(0, std::min((int)customers.size() / 3, MAX_POST_SORT_SWAPS));
    for (int i = 0; i < num_swaps; ++i) {
        int idx1 = getRandomNumber(0, customers.size() - 1);
        int idx2 = getRandomNumber(0, customers.size() - 1);
        if (idx1 != idx2) {
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}