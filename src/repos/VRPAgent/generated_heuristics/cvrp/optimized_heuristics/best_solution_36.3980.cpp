#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <utility>
#include <limits>
#include <cmath>
#include <numeric>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    if (sol.instance.numCustomers == 0) {
        return {};
    }

    const int MIN_CUSTOMERS_TO_REMOVE = 15;
    const int MAX_CUSTOMERS_TO_REMOVE = 30;
    const int MAX_EXPANSION_ATTEMPTS_WITHOUT_ADDING = 7;
    const int MAX_ATTEMPTS_FOR_NEW_SEED = 100;
    const int MAX_TOUR_CUSTOMER_ATTEMPTS = 5;
    const int MIN_GEO_NEIGHBORS_TO_CONSIDER = 10;
    const int MAX_GEO_NEIGHBORS_TO_CONSIDER = 25;

    const double PROB_SELECT_FROM_SAME_TOUR = 0.65;
    const double PROB_SELECT_NEIGHBOR_BASE = 0.55;
    const double PROB_SELECT_NEIGHBOR_SAME_TOUR_BOOST = 0.30; 

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    if (sol.instance.numCustomers < numCustomersToRemove) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        return {};
    }

    std::vector<char> isSelected(sol.instance.numCustomers + 1, 0); 
    std::vector<int> selectedCustomersList;
    selectedCustomersList.reserve(numCustomersToRemove);

    std::vector<int> expansionPool;
    expansionPool.reserve(numCustomersToRemove);

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    isSelected[seedCustomer] = 1;
    selectedCustomersList.push_back(seedCustomer);
    expansionPool.push_back(seedCustomer);

    int attemptsWithoutAdding = 0;

    while (selectedCustomersList.size() < (size_t)numCustomersToRemove) {
        if (expansionPool.empty() || attemptsWithoutAdding >= MAX_EXPANSION_ATTEMPTS_WITHOUT_ADDING) {
            int newSeed = -1;
            int attempts = 0;
            while (attempts < MAX_ATTEMPTS_FOR_NEW_SEED && selectedCustomersList.size() < sol.instance.numCustomers) {
                int tempSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (!isSelected[tempSeed]) {
                    newSeed = tempSeed;
                    break;
                }
                attempts++;
            }
            if (newSeed == -1) { 
                break; 
            }
            isSelected[newSeed] = 1;
            selectedCustomersList.push_back(newSeed);
            expansionPool.push_back(newSeed);
            attemptsWithoutAdding = 0;
            if (selectedCustomersList.size() >= (size_t)numCustomersToRemove) {
                break;
            }
        }

        int poolIdx = getRandomNumber(0, (int)expansionPool.size() - 1);
        int currentCustomer = expansionPool[poolIdx];

        std::swap(expansionPool[poolIdx], expansionPool.back());
        expansionPool.pop_back();

        int candidateCustomerToAdd = -1;
        int currentCustomerTourId = sol.customerToTourMap[currentCustomer];

        if (getRandomFractionFast() < PROB_SELECT_FROM_SAME_TOUR) {
            if (currentCustomerTourId != -1 && currentCustomerTourId < (int)sol.tours.size() && sol.tours[currentCustomerTourId].customers.size() > 1) {
                const Tour& current_tour = sol.tours[currentCustomerTourId];
                int attempts = 0;
                while (attempts < MAX_TOUR_CUSTOMER_ATTEMPTS) {
                    int random_idx_in_tour = getRandomNumber(0, (int)current_tour.customers.size() - 1);
                    int potentialCustomer = current_tour.customers[random_idx_in_tour];
                    if (potentialCustomer != currentCustomer && potentialCustomer != 0 && !isSelected[potentialCustomer]) {
                        candidateCustomerToAdd = potentialCustomer;
                        break;
                    }
                    attempts++;
                }
            }
        }

        if (candidateCustomerToAdd == -1) {
            int neighborsToProcessLimit = getRandomNumber(MIN_GEO_NEIGHBORS_TO_CONSIDER, MAX_GEO_NEIGHBORS_TO_CONSIDER);
            int neighborsProcessed = 0;
            for (int neighborNodeId : sol.instance.adj[currentCustomer]) {
                if (selectedCustomersList.size() >= (size_t)numCustomersToRemove || neighborsProcessed >= neighborsToProcessLimit) {
                    break;
                }
                if (neighborNodeId == 0) continue;
                if (isSelected[neighborNodeId]) continue;

                double probToUse = PROB_SELECT_NEIGHBOR_BASE;
                if (currentCustomerTourId != -1 && sol.customerToTourMap[neighborNodeId] == currentCustomerTourId) {
                    probToUse = std::min(1.0, probToUse + PROB_SELECT_NEIGHBOR_SAME_TOUR_BOOST);
                }

                if (getRandomFractionFast() < probToUse) {
                    candidateCustomerToAdd = neighborNodeId;
                    break;
                }
                neighborsProcessed++;
            }
        }

        if (candidateCustomerToAdd != -1) {
            isSelected[candidateCustomerToAdd] = 1;
            selectedCustomersList.push_back(candidateCustomerToAdd);
            expansionPool.push_back(candidateCustomerToAdd);
            attemptsWithoutAdding = 0;
        } else {
            attemptsWithoutAdding++;
        }
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() <= 1) {
        return;
    }

    enum SortStrategy {
        DISTANCE_TO_ANCHOR,
        DEMAND_OR_DEPOT_DIST,
        CONNECTIVITY_SCORE,
        RANDOM_SHUFFLE
    };

    const float PROB_STRATEGY_DISTANCE_TO_ANCHOR = 0.645f; 
    const float PROB_STRATEGY_DEMAND_OR_DEPOT_DIST = 0.185f; 
    const float PROB_STRATEGY_CONNECTIVITY_SCORE = 0.12f; 
    const float PROB_STRATEGY_RANDOM_SHUFFLE = 0.05f;

    const float PROB_SORT_ASCENDING = 0.5f;
    const float DISTANCE_SORT_PERTURBATION_FACTOR = 0.10f;
    const float GENERAL_SCORE_NOISE_FACTOR = 0.015f; 
    const float ALTERNATIVE_SORT_PERTURBATION_EPSILON = 0.001f;

    const float PROB_ANCHOR_IS_DEPOT = 0.148f;
    const float PROB_ANCHOR_IS_HIGH_VALUE_REMOVED = 0.105f; 

    const float PROB_SUB_STRATEGY_DEMAND_ONLY = 0.33f;
    const float PROB_SUB_STRATEGY_DEPOT_DIST_ONLY = 0.66f; 

    const int MAX_POST_SORT_SWAPS = 2;


    std::vector<std::pair<SortStrategy, float>> strategy_probs = {
        {DISTANCE_TO_ANCHOR,       PROB_STRATEGY_DISTANCE_TO_ANCHOR},
        {DEMAND_OR_DEPOT_DIST,     PROB_STRATEGY_DEMAND_OR_DEPOT_DIST},
        {CONNECTIVITY_SCORE,       PROB_STRATEGY_CONNECTIVITY_SCORE},
        {RANDOM_SHUFFLE,           PROB_STRATEGY_RANDOM_SHUFFLE}
    };

    float rand_val = getRandomFractionFast();
    SortStrategy chosenStrategy = RANDOM_SHUFFLE;
    float cumulative_prob = 0.0f;
    for (const auto& p : strategy_probs) {
        cumulative_prob += p.second;
        if (rand_val <= cumulative_prob) {
            chosenStrategy = p.first;
            break;
        }
    }

    bool sortAscending = (getRandomFractionFast() < PROB_SORT_ASCENDING);

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    switch (chosenStrategy) {
        case DISTANCE_TO_ANCHOR: {
            int anchorCustomer = -1;
            double anchor_selection_rand = getRandomFractionFast();

            if (anchor_selection_rand < PROB_ANCHOR_IS_DEPOT) {
                anchorCustomer = 0; 
            } else if (anchor_selection_rand < PROB_ANCHOR_IS_DEPOT + PROB_ANCHOR_IS_HIGH_VALUE_REMOVED) { 
                float max_score = -1.0f;
                anchorCustomer = customers[0]; 
                for (int customerId : customers) {
                    float current_score = static_cast<float>(instance.demand[customerId]) + instance.distanceMatrix[0][customerId] * 0.1f;
                    if (current_score > max_score) {
                        max_score = current_score;
                        anchorCustomer = customerId;
                    }
                }
            } else {
                anchorCustomer = customers[getRandomNumber(0, customers.size() - 1)]; 
            }

            for (int customerId : customers) {
                float score = instance.distanceMatrix[anchorCustomer][customerId];
                score *= (1.0f + getRandomFractionFast() * DISTANCE_SORT_PERTURBATION_FACTOR);
                scoredCustomers.push_back({score, customerId});
            }
            break;
        }

        case DEMAND_OR_DEPOT_DIST: {
            double sub_strategy_choice = getRandomFractionFast();
            for (int customerId : customers) {
                float score;
                if (sub_strategy_choice < PROB_SUB_STRATEGY_DEMAND_ONLY) {
                    score = static_cast<float>(instance.demand[customerId]);
                } else if (sub_strategy_choice < PROB_SUB_STRATEGY_DEPOT_DIST_ONLY) {
                    score = instance.distanceMatrix[0][customerId];
                } else {
                    float demand_weight = 1.0f + getRandomFractionFast() * 0.5f;
                    float depot_distance_weight = 0.1f + getRandomFractionFast() * 0.1f;
                    score = static_cast<float>(instance.demand[customerId]) * demand_weight;
                    score += instance.distanceMatrix[0][customerId] * depot_distance_weight;
                }
                score *= (1.0f + (getRandomFractionFast() - 0.5f) * GENERAL_SCORE_NOISE_FACTOR);
                score += getRandomFractionFast() * ALTERNATIVE_SORT_PERTURBATION_EPSILON;
                scoredCustomers.push_back({score, customerId});
            }
            break;
        }

        case CONNECTIVITY_SCORE: {
            for (int c1 : customers) {
                float connectivityScore = 0.0f;
                for (int c2 : customers) {
                    if (c1 != c2) {
                        float dist = instance.distanceMatrix[c1][c2];
                        connectivityScore += 1.0f / (dist + 0.0001f); 
                    }
                }
                connectivityScore *= (1.0f + (getRandomFractionFast() - 0.5f) * GENERAL_SCORE_NOISE_FACTOR);
                connectivityScore += getRandomFractionFast() * ALTERNATIVE_SORT_PERTURBATION_EPSILON;
                scoredCustomers.push_back({connectivityScore, c1});
            }
            break;
        }

        case RANDOM_SHUFFLE: {
            static thread_local std::mt19937 gen(std::random_device{}());
            std::shuffle(customers.begin(), customers.end(), gen);
            return;
        }
    }

    if (sortAscending) {
        std::sort(scoredCustomers.begin(), scoredCustomers.end(),
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                      return a.first < b.first;
                  });
    } else {
        std::sort(scoredCustomers.begin(), scoredCustomers.end(),
                  [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                      return a.first > b.first;
                  });
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
    
    int numSwaps = getRandomNumber(0, std::min((int)customers.size() / 5, MAX_POST_SORT_SWAPS));
    for (int k = 0; k < numSwaps; ++k) {
        if (customers.size() < 2) break;
        int idx1 = getRandomNumber(0, (int)customers.size() - 1);
        int idx2 = getRandomNumber(0, (int)customers.size() - 1);
        if (idx1 != idx2) {
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}