#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <utility>
#include <cmath>
#include <limits>
#include <algorithm> // For std::min, std::shuffle, std::sort

static thread_local std::mt19937 generator(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int NUM_CUSTOMERS_TO_REMOVE_MIN = 8;
    const int NUM_CUSTOMERS_TO_REMOVE_MAX = 15;
    const float PROB_TRY_SERVED_FIRST = 0.80f;
    const int SEED_SEARCH_ATTEMPTS = 60;
    const int POTENTIAL_CANDIDATES_RESERVE_SIZE = 40;
    const int NEIGHBORS_CONSIDER_MIN = 7;
    const int NEIGHBORS_CONSIDER_MAX = 16;
    const float PROB_INCLUDE_ADJ_NEIGHBOR = 0.895f;
    const float PROB_ADD_SELECTED_CANDIDATE = 0.80f;
    const int RANDOM_CUSTOMER_RETRY_ATTEMPTS = 15;

    int numCustomersToRemove = getRandomNumber(NUM_CUSTOMERS_TO_REMOVE_MIN, NUM_CUSTOMERS_TO_REMOVE_MAX);
    // Using std::vector<char> instead of std::unordered_set<int> for O(1) average time
    // complexity for checking and marking selected customers, avoiding hashing overhead.
    // Initialize all to 0 (false). Size numCustomers + 1 for 1-based indexing.
    std::vector<char> isSelected(sol.instance.numCustomers + 1, 0); 
    std::vector<int> selectedCustomersList;
    selectedCustomersList.reserve(static_cast<size_t>(numCustomersToRemove));

    const Instance& instance = sol.instance;

    int initialSeed = -1;
    bool tryServedFirst = (getRandomFraction() < PROB_TRY_SERVED_FIRST);

    if (tryServedFirst) {
        for (int i = 0; i < SEED_SEARCH_ATTEMPTS; ++i) {
            int potentialSeed = getRandomNumber(1, instance.numCustomers);
            if (sol.customerToTourMap[potentialSeed] != -1) {
                initialSeed = potentialSeed;
                break;
            }
        }
    }
    
    if (initialSeed == -1) { // If no served customer found or not trying served first
        for (int i = 0; i < SEED_SEARCH_ATTEMPTS; ++i) {
            int potentialSeed = getRandomNumber(1, instance.numCustomers);
            if (sol.customerToTourMap[potentialSeed] == -1) { // Prefer unserved customers
                initialSeed = potentialSeed;
                break;
            }
        }
    }

    if (initialSeed == -1) { // Fallback to any random customer if preferred types not found
        initialSeed = getRandomNumber(1, instance.numCustomers);
    }
    
    isSelected[initialSeed] = 1; // Mark as selected
    selectedCustomersList.push_back(initialSeed);

    const size_t targetNumCustomers = static_cast<size_t>(numCustomersToRemove);
    // Reuse potentialCandidates vector to avoid repeated allocations/deallocations
    std::vector<int> potentialCandidates;
    potentialCandidates.reserve(POTENTIAL_CANDIDATES_RESERVE_SIZE);

    while (selectedCustomersList.size() < targetNumCustomers) {
        int customerFromListIdx = getRandomNumber(0, static_cast<int>(selectedCustomersList.size()) - 1);
        int customerFromList = selectedCustomersList[customerFromListIdx];

        potentialCandidates.clear(); // Clear for current iteration, preserving capacity
        
        int neighborsToConsider = std::min(static_cast<int>(instance.adj[customerFromList].size()), getRandomNumber(NEIGHBORS_CONSIDER_MIN, NEIGHBORS_CONSIDER_MAX)); 
        for (int i = 0; i < neighborsToConsider; ++i) {
             int neighborNodeId = instance.adj[customerFromList][i];
             if (neighborNodeId == 0) continue; // Skip depot
             if (isSelected[neighborNodeId]) continue; // O(1) check
             if (getRandomFractionFast() < PROB_INCLUDE_ADJ_NEIGHBOR) {
                potentialCandidates.push_back(neighborNodeId);
             }
        }

        int tourIdx = sol.customerToTourMap[customerFromList];
        if (tourIdx != -1 && tourIdx < static_cast<int>(sol.tours.size())) {
            const Tour& tour = sol.tours[tourIdx];
            for (int c : tour.customers) {
                if (c == customerFromList || c == 0) continue;
                if (isSelected[c]) continue; // O(1) check
                potentialCandidates.push_back(c);
            }
        }

        std::shuffle(potentialCandidates.begin(), potentialCandidates.end(), generator);

        bool addedNewCustomerThisIteration = false;
        for (int candidate : potentialCandidates) {
            if (selectedCustomersList.size() >= targetNumCustomers) break;
            if (!isSelected[candidate]) { // O(1) check
                if (getRandomFractionFast() < PROB_ADD_SELECTED_CANDIDATE) {
                    isSelected[candidate] = 1; // O(1) mark
                    selectedCustomersList.push_back(candidate);
                    addedNewCustomerThisIteration = true;
                }
            }
        }

        if (!addedNewCustomerThisIteration && selectedCustomersList.size() < targetNumCustomers) {
            bool foundTotallyRandom = false;
            for (int retry = 0; retry < RANDOM_CUSTOMER_RETRY_ATTEMPTS; ++retry) {
                int potentialNewCustomer = getRandomNumber(1, instance.numCustomers);
                if (!isSelected[potentialNewCustomer]) { // O(1) check
                    isSelected[potentialNewCustomer] = 1; // O(1) mark
                    selectedCustomersList.push_back(potentialNewCustomer);
                    foundTotallyRandom = true;
                    break;
                }
            }
            if (!foundTotallyRandom) {
                // Should be rare, but prevents infinite loop if customers are exhausted.
                break; 
            }
        }
    }
    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    const float PRIZE_MULT_OFFSET_RANGE = 0.13f;
    const float DIST_DEPOT_MULT_OFFSET_RANGE = 0.07f;
    const float DEMAND_MULT_OFFSET_RANGE = 0.06f;
    const float DENOMINATOR_OFFSET = 1.0f;
    const float NOISE_FACTOR = 0.145f;
    const float MIN_NOISE_ABS = 0.12f;
    const float PENALTY_MULT_BASE = 0.005f;
    const float PENALTY_MULT_NOISE_RANGE = 0.001f;
    const float PROB_APPLY_STRATEGY_SHIFT = 0.11f;
    const float STRATEGY_SHIFT_MAGNITUDE_PRIZE_MIN = 0.085f;
    const float STRATEGY_SHIFT_MAGNITUDE_PRIZE_MAX = 0.17f;
    const float STRATEGY_SHIFT_MAGNITUDE_DIST_MIN = 0.045f;
    const float STRATEGY_SHIFT_MAGNITUDE_DIST_MAX = 0.086f;
    const float STRATEGY_SHIFT_MAGNITUDE_DEMAND_MIN = 0.044f;
    const float STRATEGY_SHIFT_MAGNITUDE_DEMAND_MAX = 0.085f;
    const float EPSILON_PRIZE_NEGLIGIBLE = 1e-5f; 

    if (customers.empty()) {
        return;
    }

    bool allPrizesNegligible = true;
    for (int customerId : customers) {
        if (static_cast<float>(instance.prizes[customerId]) > EPSILON_PRIZE_NEGLIGIBLE) {
            allPrizesNegligible = false;
            break;
        }
    }

    if (allPrizesNegligible) {
        std::shuffle(customers.begin(), customers.end(), generator);
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    float prize_mult = 1.0f + getRandomFraction(-PRIZE_MULT_OFFSET_RANGE, PRIZE_MULT_OFFSET_RANGE);
    float dist_depot_mult = 1.0f + getRandomFraction(-DIST_DEPOT_MULT_OFFSET_RANGE, DIST_DEPOT_MULT_OFFSET_RANGE);
    float demand_mult = 1.0f + getRandomFraction(-DEMAND_MULT_OFFSET_RANGE, DEMAND_MULT_OFFSET_RANGE);
    float penalty_mult = PENALTY_MULT_BASE + getRandomFraction(-PENALTY_MULT_NOISE_RANGE, PENALTY_MULT_NOISE_RANGE);

    if (getRandomFractionFast() < PROB_APPLY_STRATEGY_SHIFT) {
        float strategyChoice = getRandomFractionFast();
        if (strategyChoice < 0.33f) {
            prize_mult *= (1.0f + getRandomFraction(STRATEGY_SHIFT_MAGNITUDE_PRIZE_MIN, STRATEGY_SHIFT_MAGNITUDE_PRIZE_MAX));
        } else if (strategyChoice < 0.66f) {
            dist_depot_mult *= (1.0f - getRandomFraction(STRATEGY_SHIFT_MAGNITUDE_DIST_MIN, STRATEGY_SHIFT_MAGNITUDE_DIST_MAX));
        } else {
            demand_mult *= (1.0f + getRandomFraction(STRATEGY_SHIFT_MAGNITUDE_DEMAND_MIN, STRATEGY_SHIFT_MAGNITUDE_DEMAND_MAX));
        }
    }

    for (int customerId : customers) {
        float prize = static_cast<float>(instance.prizes[customerId]);
        float distToDepot = static_cast<float>(instance.distanceMatrix[0][customerId]);
        float demand = static_cast<float>(instance.demand[customerId]);
        
        float score_numerator = prize * prize_mult;
        float score_denominator = (distToDepot * dist_depot_mult) + (demand * demand_mult) + DENOMINATOR_OFFSET;
        
        if (score_denominator < std::numeric_limits<float>::epsilon()) {
            score_denominator = std::numeric_limits<float>::epsilon(); 
        }

        float score = score_numerator / score_denominator;

        score -= (distToDepot * penalty_mult);

        float noiseRange = NOISE_FACTOR * std::abs(score); 
        if (noiseRange < MIN_NOISE_ABS) noiseRange = MIN_NOISE_ABS; 
        float randomNoise = (getRandomFraction() * 2.0f - 1.0f) * noiseRange; 
        
        float finalScore = score + randomNoise;

        if (std::isnan(finalScore) || std::isinf(finalScore)) {
            finalScore = score; 
        }

        scoredCustomers.push_back({finalScore, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Directly populate the 'customers' vector from sorted 'scoredCustomers'
    // This avoids an intermediate vector and potentially less efficient repeated
    // swap/pop_back operations on 'scoredCustomers'.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}