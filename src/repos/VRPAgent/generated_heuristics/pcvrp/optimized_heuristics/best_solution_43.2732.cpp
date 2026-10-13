#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <utility>

static thread_local std::mt19937 gen_select(std::random_device{}());
static thread_local std::mt19937 gen_sort(std::random_device{}());

const int LNS_MIN_CUSTOMERS_TO_REMOVE = 6;
const int LNS_MAX_CUSTOMERS_TO_REMOVE = 18;
const int LNS_SELECT_MAX_SEED_ATTEMPTS_UNVISITED = 50;
const float LNS_SELECT_SEED_FROM_TOUR_PROB = 0.72f;
const float LNS_SELECT_SEED_FROM_UNSERVED_PROB = 0.85f; 
const float LNS_TOUR_SEGMENT_EXPAND_FROM_SEED_PROB = 0.56f;
const size_t LNS_MAX_TOUR_EXPLORATION_LENGTH_SELECT = 150;
const float LNS_TOUR_NEIGHBOR_SELECTION_PROB = 0.86f;
const float LNS_ADJ_BASE_SELECTION_PROB = 0.79f;
const float LNS_ADJ_PROB_JITTER_RANGE = 0.04f;
const int LNS_MIN_ADJ_NEIGHBORS_TO_CONSIDER = 5;
const int LNS_MAX_ADJ_NEIGHBORS_TO_EXPLORE_SELECT = 22;
const int LNS_MAX_TOUR_SAMPLES_FROM_CURRENT_CUSTOMER = 4;
const float LNS_SELECT_ADJ_PROB_MIN_FACTOR = 0.09f;

const float LNS_RANDOM_SHUFFLE_PROBABILITY_SORT = 0.095f;
const float LNS_BASE_NOISE_FACTOR_SORT = 0.055f;
const float LNS_NOISE_MAGNITUDE_JITTER_RANGE = 0.2f;
const float LNS_PROB_STOCHASTIC_POOL_SORT = 0.13f;
const int LNS_POOL_SIZE_FOR_STOCHASTIC_SORT_MIN = 3;
const int LNS_POOL_SIZE_FOR_STOCHASTIC_SORT_MAX = 5;
const float LNS_CLUSTER_INVERSE_DIST_MULTIPLIER = 0.1f;
const float LNS_DEMAND_PENALTY_BASE_SORT = 0.007f;
const float LNS_DEMAND_PENALTY_JITTER_RANGE_SORT = 0.006f;
const float LNS_ADJ_WEIGHT_MIN_SORT = 0.00015f;
const float LNS_ADJ_WEIGHT_MAX_SORT = 0.0005f;
const float LNS_STOCH_PRIZE_FACTOR_MIN = 0.90f;
const float LNS_STOCH_PRIZE_FACTOR_MAX = 1.10f;
const float LNS_STOCH_DIST_FACTOR_MIN = 0.95f;
const float LNS_STOCH_DIST_FACTOR_MAX = 1.05f;
const float LNS_STOCH_DEMAND_PENALTY_MIX = 0.007f;

const float LNS_PROB_COMPLEX_MIX_DEMAND_PENALTY_INTERNAL = 0.60f;
const float LNS_DEMAND_PENALTY_MIX_MIN_INTERNAL = 0.005f;
const float LNS_DEMAND_PENALTY_MIX_MAX_INTERNAL = 0.015f;
const float LNS_ADJ_WEIGHT_MIX_MIN_INTERNAL = 0.0001f;
const float LNS_ADJ_WEIGHT_MIX_MAX_INTERNAL = 0.0003f;

const float LNS_CUM_PROB_PRIZE_DIV_DIST_DEPOT = 0.10f;
const float LNS_CUM_PROB_COMPLEX_MIX_WITH_ADJ = 0.20f;
const float LNS_CUM_PROB_NETWORK_CENTRALITY_PRIORITY = 0.30f;
const float LNS_CUM_PROB_PRIZE_MINUS_DIST_TO_DEPOT = 0.40f;
const float LNS_CUM_PROB_PRIZE_ONLY = 0.50f;
const float LNS_CUM_PROB_PRIZE_PER_DEMAND = 0.60f;
const float LNS_CUM_PROB_NEG_DIST_TO_DEPOT = 0.70f;
const float LNS_CUM_PROB_CLUSTER_PRIORITY = 0.78f;
const float LNS_CUM_PROB_ADJACENCY_DEMAND_MIX_STRATEGY = 0.85f;
const float LNS_CUM_PROB_INTERNAL_CONNECTIVITY_PRIORITY = 0.93f;
const float LNS_CUM_PROB_STOCHASTIC_PRIZE_DIST_MIX = 1.00f;


std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<char> isSelected(sol.instance.numCustomers + 1, 0); 
    std::vector<int> selectedCustomersList;
    std::vector<int> customersToExploreQueue;
    const Instance& instance = sol.instance;

    int numCustomersToRemove = getRandomNumber(LNS_MIN_CUSTOMERS_TO_REMOVE, LNS_MAX_CUSTOMERS_TO_REMOVE);
    numCustomersToRemove = std::min(numCustomersToRemove, instance.numCustomers);
    
    if (numCustomersToRemove == 0 || instance.numCustomers == 0) {
        return {};
    }

    selectedCustomersList.reserve(numCustomersToRemove);
    customersToExploreQueue.reserve(numCustomersToRemove + LNS_MAX_TOUR_EXPLORATION_LENGTH_SELECT + LNS_MAX_ADJ_NEIGHBORS_TO_EXPLORE_SELECT);

    int initialSeedCustomer = -1;

    float seedChoiceRoll = getRandomFractionFast();
    if (seedChoiceRoll < LNS_SELECT_SEED_FROM_TOUR_PROB) {
        if (!sol.tours.empty()) {
            int random_tour_idx = getRandomNumber(0, sol.tours.size() - 1);
            if (!sol.tours[random_tour_idx].customers.empty()) {
                initialSeedCustomer = sol.tours[random_tour_idx].customers[getRandomNumber(0, sol.tours[random_tour_idx].customers.size() - 1)];
            }
        }
    }
    
    if (initialSeedCustomer == -1 && seedChoiceRoll < LNS_SELECT_SEED_FROM_UNSERVED_PROB) {
        for (int attempt = 0; attempt < LNS_SELECT_MAX_SEED_ATTEMPTS_UNVISITED; ++attempt) {
            int random_customer_id = getRandomNumber(1, instance.numCustomers);
            if (random_customer_id > 0 && random_customer_id <= instance.numCustomers && sol.customerToTourMap[random_customer_id] == -1) {
                initialSeedCustomer = random_customer_id;
                break;
            }
        }
    }

    if (initialSeedCustomer == -1 || initialSeedCustomer == 0) {
        if (instance.numCustomers >= 1) {
            initialSeedCustomer = getRandomNumber(1, instance.numCustomers);
        } else {
            return {};
        }
    }
    
    selectedCustomersList.push_back(initialSeedCustomer);
    isSelected[initialSeedCustomer] = 1;
    customersToExploreQueue.push_back(initialSeedCustomer);

    if (sol.customerToTourMap[initialSeedCustomer] != -1 && getRandomFractionFast() < LNS_TOUR_SEGMENT_EXPAND_FROM_SEED_PROB) {
        const Tour& tour = sol.tours[sol.customerToTourMap[initialSeedCustomer]];
        if (!tour.customers.empty() && tour.customers.size() <= LNS_MAX_TOUR_EXPLORATION_LENGTH_SELECT) {
            int initialSeedIndexInTour = -1;
            for (size_t i = 0; i < tour.customers.size(); ++i) {
                if (tour.customers[i] == initialSeedCustomer) {
                    initialSeedIndexInTour = i;
                    break;
                }
            }

            if (initialSeedIndexInTour != -1) {
                for (int i = initialSeedIndexInTour - 1; i >= 0; --i) {
                    if (selectedCustomersList.size() >= numCustomersToRemove) break;
                    int customer = tour.customers[i];
                    if (customer != 0 && isSelected[customer] == 0) {
                        selectedCustomersList.push_back(customer);
                        isSelected[customer] = 1;
                        customersToExploreQueue.push_back(customer);
                    }
                }
                for (size_t i = initialSeedIndexInTour + 1; i < tour.customers.size(); ++i) {
                    if (selectedCustomersList.size() >= numCustomersToRemove) break;
                    int customer = tour.customers[i];
                    if (customer != 0 && isSelected[customer] == 0) {
                        selectedCustomersList.push_back(customer);
                        isSelected[customer] = 1;
                        customersToExploreQueue.push_back(customer);
                    }
                }
            }
        }
    }

    size_t currentExplorationQueueIdx = 0;
    std::vector<int> potentialNewCandidates;
    potentialNewCandidates.reserve(LNS_MAX_ADJ_NEIGHBORS_TO_EXPLORE_SELECT + 2 + LNS_MAX_TOUR_SAMPLES_FROM_CURRENT_CUSTOMER);

    while (selectedCustomersList.size() < numCustomersToRemove && currentExplorationQueueIdx < customersToExploreQueue.size()) {
        int currentCustomerToExpandFrom = customersToExploreQueue[currentExplorationQueueIdx++];

        potentialNewCandidates.clear();

        if (sol.customerToTourMap[currentCustomerToExpandFrom] != -1) {
            const Tour& tour = sol.tours[sol.customerToTourMap[currentCustomerToExpandFrom]];
            for (size_t i = 0; i < tour.customers.size(); ++i) {
                if (tour.customers[i] == currentCustomerToExpandFrom) {
                    if (i > 0) {
                        int prev_customer = tour.customers[i-1];
                        if (prev_customer != 0 && isSelected[prev_customer] == 0 && getRandomFractionFast() < LNS_TOUR_NEIGHBOR_SELECTION_PROB) {
                            potentialNewCandidates.push_back(prev_customer);
                        }
                    }
                    if (i < tour.customers.size() - 1) {
                        int next_customer = tour.customers[i+1];
                        if (next_customer != 0 && isSelected[next_customer] == 0 && getRandomFractionFast() < LNS_TOUR_NEIGHBOR_SELECTION_PROB) {
                            potentialNewCandidates.push_back(next_customer);
                        }
                    }
                    break;
                }
            }
            int num_customers_in_tour = tour.customers.size();
            if (num_customers_in_tour > 1) {
                int num_to_sample = getRandomNumber(1, std::min(LNS_MAX_TOUR_SAMPLES_FROM_CURRENT_CUSTOMER, num_customers_in_tour - 1));
                for (int k = 0; k < num_to_sample; ++k) {
                    int random_idx = getRandomNumber(0, num_customers_in_tour - 1);
                    int potential_neighbor = tour.customers[random_idx];
                    if (potential_neighbor != 0 && potential_neighbor != currentCustomerToExpandFrom && isSelected[potential_neighbor] == 0) {
                        potentialNewCandidates.push_back(potential_neighbor);
                    }
                }
            }
        }

        if (currentCustomerToExpandFrom > 0 && static_cast<size_t>(currentCustomerToExpandFrom) < instance.adj.size() && !instance.adj[currentCustomerToExpandFrom].empty()) {
            const std::vector<int>& adj_neighbors = instance.adj[currentCustomerToExpandFrom];
            
            int effectiveMaxAdjNeighbors = std::min((int)adj_neighbors.size(), LNS_MAX_ADJ_NEIGHBORS_TO_EXPLORE_SELECT);
            int actualNeighborsToConsider = 0;
            if (effectiveMaxAdjNeighbors > 0) {
                 actualNeighborsToConsider = getRandomNumber(std::min(LNS_MIN_ADJ_NEIGHBORS_TO_CONSIDER, effectiveMaxAdjNeighbors), effectiveMaxAdjNeighbors);
            }
            actualNeighborsToConsider = std::min(actualNeighborsToConsider, (int)adj_neighbors.size());

            float currentAdjSelectionProbability = LNS_ADJ_BASE_SELECTION_PROB + getRandomFraction(-LNS_ADJ_PROB_JITTER_RANGE, LNS_ADJ_PROB_JITTER_RANGE);
            currentAdjSelectionProbability = std::max(0.0f, std::min(1.0f, currentAdjSelectionProbability));

            for (int i = 0; i < actualNeighborsToConsider; ++i) {
                int neighbor = adj_neighbors[i];
                if (neighbor == 0) continue;
                if (isSelected[neighbor] == 0) {
                    float probFactor = 1.0f - (float)i / (float)actualNeighborsToConsider;
                    probFactor = std::max(LNS_SELECT_ADJ_PROB_MIN_FACTOR, probFactor);
                    if (getRandomFractionFast() < currentAdjSelectionProbability * probFactor) {
                        potentialNewCandidates.push_back(neighbor);
                    }
                }
            }
        }

        if (!potentialNewCandidates.empty()) {
            std::shuffle(potentialNewCandidates.begin(), potentialNewCandidates.end(), gen_select);
            for (int candidate : potentialNewCandidates) {
                if (selectedCustomersList.size() >= numCustomersToRemove) {
                    break;
                }
                if (isSelected[candidate] == 0) {
                    selectedCustomersList.push_back(candidate);
                    isSelected[candidate] = 1;
                    customersToExploreQueue.push_back(candidate);
                }
            }
        }
    }

    while (selectedCustomersList.size() < numCustomersToRemove) {
        if (instance.numCustomers == 0) break;
        int newSeed = getRandomNumber(1, instance.numCustomers);
        if (newSeed > 0 && newSeed <= instance.numCustomers && isSelected[newSeed] == 0) {
            selectedCustomersList.push_back(newSeed);
            isSelected[newSeed] = 1;
        }
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    if (getRandomFractionFast() < LNS_RANDOM_SHUFFLE_PROBABILITY_SORT) {
        std::shuffle(customers.begin(), customers.end(), gen_sort);
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    bool ascending_sort_order = getRandomFractionFast() < 0.5;

    enum SortStrategy {
        PRIZE_DIV_DIST_DEPOT,
        COMPLEX_MIX_WITH_ADJ,
        NETWORK_CENTRALITY_PRIORITY,
        PRIZE_MINUS_DIST_TO_DEPOT,
        PRIZE_ONLY,
        PRIZE_PER_DEMAND,
        NEG_DIST_TO_DEPOT,
        CLUSTER_PRIORITY,
        ADJACENCY_DEMAND_MIX_STRATEGY,
        INTERNAL_CONNECTIVITY_PRIORITY,
        STOCHASTIC_PRIZE_DIST_MIX,
        NUM_SORT_STRATEGIES
    };

    SortStrategy strategy;
    float strategy_roll = getRandomFractionFast();
    if (strategy_roll < LNS_CUM_PROB_PRIZE_DIV_DIST_DEPOT) {
        strategy = PRIZE_DIV_DIST_DEPOT;
    } else if (strategy_roll < LNS_CUM_PROB_COMPLEX_MIX_WITH_ADJ) {
        strategy = COMPLEX_MIX_WITH_ADJ;
    } else if (strategy_roll < LNS_CUM_PROB_NETWORK_CENTRALITY_PRIORITY) {
        strategy = NETWORK_CENTRALITY_PRIORITY;
    } else if (strategy_roll < LNS_CUM_PROB_PRIZE_MINUS_DIST_TO_DEPOT) {
        strategy = PRIZE_MINUS_DIST_TO_DEPOT;
    } else if (strategy_roll < LNS_CUM_PROB_PRIZE_ONLY) {
        strategy = PRIZE_ONLY;
    } else if (strategy_roll < LNS_CUM_PROB_PRIZE_PER_DEMAND) {
        strategy = PRIZE_PER_DEMAND;
    } else if (strategy_roll < LNS_CUM_PROB_NEG_DIST_TO_DEPOT) {
        strategy = NEG_DIST_TO_DEPOT;
    } else if (strategy_roll < LNS_CUM_PROB_CLUSTER_PRIORITY) {
        strategy = CLUSTER_PRIORITY;
    } else if (strategy_roll < LNS_CUM_PROB_ADJACENCY_DEMAND_MIX_STRATEGY) {
        strategy = ADJACENCY_DEMAND_MIX_STRATEGY;
    } else if (strategy_roll < LNS_CUM_PROB_INTERNAL_CONNECTIVITY_PRIORITY) {
        strategy = INTERNAL_CONNECTIVITY_PRIORITY;
    } else {
        strategy = STOCHASTIC_PRIZE_DIST_MIX;
    }

    float average_prize_per_customer = (instance.numCustomers > 0) ? (static_cast<float>(instance.total_prizes) / instance.numCustomers) : 100.0f;
    float baseNoiseMagnitude = std::max(0.001f, average_prize_per_customer * LNS_BASE_NOISE_FACTOR_SORT);
    baseNoiseMagnitude *= (1.0f + getRandomFraction(-LNS_NOISE_MAGNITUDE_JITTER_RANGE, LNS_NOISE_MAGNITUDE_JITTER_RANGE));
    baseNoiseMagnitude = std::max(0.001f, baseNoiseMagnitude);

    for (int customer : customers) {
        float score;
        float prize_val = static_cast<float>(instance.prizes[customer]);
        float dist_to_depot_val = static_cast<float>(instance.distanceMatrix[0][customer]);
        float demand_val = static_cast<float>(instance.demand[customer]);
        size_t num_adj_neighbors = (customer > 0 && static_cast<size_t>(customer) < instance.adj.size()) ? instance.adj[customer].size() : 0;
        
        float safe_dist_divisor = dist_to_depot_val + 1.0f;
        float safe_demand_divisor = demand_val + 1.0f;

        switch (strategy) {
            case PRIZE_DIV_DIST_DEPOT:
                score = prize_val / safe_dist_divisor;
                score += static_cast<float>(num_adj_neighbors) * getRandomFraction(LNS_ADJ_WEIGHT_MIN_SORT, LNS_ADJ_WEIGHT_MAX_SORT);
                break;
            case COMPLEX_MIX_WITH_ADJ:
                if (getRandomFractionFast() < LNS_PROB_COMPLEX_MIX_DEMAND_PENALTY_INTERNAL) {
                     score = (prize_val / safe_dist_divisor) - (demand_val * getRandomFraction(LNS_DEMAND_PENALTY_MIX_MIN_INTERNAL, LNS_DEMAND_PENALTY_MIX_MAX_INTERNAL));
                } else {
                     score = prize_val + (static_cast<float>(num_adj_neighbors) * getRandomFraction(LNS_ADJ_WEIGHT_MIX_MIN_INTERNAL, LNS_ADJ_WEIGHT_MIX_MAX_INTERNAL));
                }
                break;
            case NETWORK_CENTRALITY_PRIORITY:
                score = (static_cast<float>(num_adj_neighbors) + 1.0f) * (prize_val / safe_dist_divisor);
                break;
            case PRIZE_MINUS_DIST_TO_DEPOT:
                score = prize_val - dist_to_depot_val;
                score += static_cast<float>(num_adj_neighbors) * getRandomFraction(LNS_ADJ_WEIGHT_MIN_SORT * 0.5f, LNS_ADJ_WEIGHT_MAX_SORT * 0.5f);
                break;
            case PRIZE_ONLY:
                score = prize_val;
                break;
            case PRIZE_PER_DEMAND:
                score = prize_val / safe_demand_divisor;
                break;
            case NEG_DIST_TO_DEPOT:
                score = -dist_to_depot_val;
                break;
            case CLUSTER_PRIORITY: {
                float inverse_dist_sum = 0.0f;
                for (int other_customer : customers) {
                    if (customer == other_customer) continue;
                    if (static_cast<size_t>(customer) < instance.distanceMatrix.size() && 
                        static_cast<size_t>(other_customer) < instance.distanceMatrix[customer].size()) {
                         inverse_dist_sum += 1.0f / (static_cast<float>(instance.distanceMatrix[customer][other_customer]) + 1.0f);
                    }
                }
                score = inverse_dist_sum * LNS_CLUSTER_INVERSE_DIST_MULTIPLIER;
                score += (prize_val / safe_dist_divisor) * 0.1f;
                break;
            }
            case ADJACENCY_DEMAND_MIX_STRATEGY:
                score = (prize_val / safe_dist_divisor) * (1.0f + static_cast<float>(num_adj_neighbors) * getRandomFraction(LNS_ADJ_WEIGHT_MIN_SORT * 10, LNS_ADJ_WEIGHT_MAX_SORT * 10));
                score -= (demand_val * getRandomFraction(LNS_DEMAND_PENALTY_BASE_SORT * 0.5f, LNS_DEMAND_PENALTY_JITTER_RANGE_SORT * 0.5f));
                break;
            case INTERNAL_CONNECTIVITY_PRIORITY: {
                float internal_connectivity_score = 0.0f;
                for (int other_customer : customers) {
                    if (customer == other_customer) continue;
                    if (static_cast<size_t>(customer) < instance.distanceMatrix.size() && 
                        static_cast<size_t>(other_customer) < instance.distanceMatrix[customer].size()) {
                        internal_connectivity_score += 1.0f / (static_cast<float>(instance.distanceMatrix[customer][other_customer]) + 1.0f);
                    }
                }
                score = internal_connectivity_score;
                score += (prize_val / safe_demand_divisor) * 0.05f; 
                break;
            }
            case STOCHASTIC_PRIZE_DIST_MIX:
                score = (prize_val * getRandomFraction(LNS_STOCH_PRIZE_FACTOR_MIN, LNS_STOCH_PRIZE_FACTOR_MAX)) / 
                        (safe_dist_divisor * getRandomFraction(LNS_STOCH_DIST_FACTOR_MIN, LNS_STOCH_DIST_FACTOR_MAX));
                score -= (demand_val * LNS_STOCH_DEMAND_PENALTY_MIX);
                score += static_cast<float>(num_adj_neighbors) * getRandomFraction(LNS_ADJ_WEIGHT_MIN_SORT * 2, LNS_ADJ_WEIGHT_MAX_SORT * 2);
                break;
            default: 
                score = prize_val / safe_dist_divisor; 
                break;
        }
        
        score += getRandomFraction(-baseNoiseMagnitude, baseNoiseMagnitude);
        
        scoredCustomers.emplace_back(score, customer);
    }

    if (getRandomFractionFast() < LNS_PROB_STOCHASTIC_POOL_SORT) {
        const int pool_size = getRandomNumber(LNS_POOL_SIZE_FOR_STOCHASTIC_SORT_MIN, LNS_POOL_SIZE_FOR_STOCHASTIC_SORT_MAX);

        std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
            return a.first > b.first; 
        });

        std::vector<int> reorderedCustomers;
        reorderedCustomers.reserve(customers.size());

        size_t current_active_size = scoredCustomers.size();
        while (current_active_size > 0) {
            const int current_pool_size_actual = std::min(static_cast<int>(current_active_size), pool_size);
            int chosen_relative_idx = (current_pool_size_actual > 0) ? getRandomNumber(0, current_pool_size_actual - 1) : 0;

            reorderedCustomers.push_back(scoredCustomers[static_cast<size_t>(chosen_relative_idx)].second);

            std::swap(scoredCustomers[static_cast<size_t>(chosen_relative_idx)], scoredCustomers[current_active_size - 1]);
            current_active_size--;
        }
        customers = reorderedCustomers;
    } else {
        std::sort(scoredCustomers.begin(), scoredCustomers.end(), [&](const std::pair<float, int>& a, const std::pair<float, int>& b) {
            if (a.first != b.first) {
                return ascending_sort_order ? (a.first < b.first) : (a.first > b.first);
            }
            return a.second < b.second;
        });

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scoredCustomers[i].second;
        }
    }
}