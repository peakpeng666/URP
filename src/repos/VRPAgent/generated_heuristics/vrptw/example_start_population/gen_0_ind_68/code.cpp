#include "AgentDesigned.h"
#include <vector>
#include <random>
#include <unordered_set>
#include <algorithm>
#include <cmath>
#include <limits>

struct NormalizationFactors {
    float max_dist;
    float max_tw_diff;
    float max_demand;
    float max_tw_width;
    float max_dist_from_depot;
};

// Heuristic parameters for select_by_llm_1
const float W_DIST_SELECT = 1.0f;
const float W_TW_SELECT = 0.5f;
const float W_DEMAND_SELECT = 0.2f;

const float ALPHA_SHATTER_PROB = 3.0f; 
const int CANDIDATE_POOL_SIZE = 20;

// Heuristic parameters for sort_by_llm_1
const float W_TW_SORT = 2.0f;
const float W_DEMAND_SORT = 1.0f;
const float W_DIST_DEPOT_SORT = 0.5f;
const float RANDOM_NOISE_SORT = 0.05f;

// Pre-calculates normalization factors for various customer attributes across the entire instance.
// This is done once per instance to optimize performance for subsequent heuristic calls.
NormalizationFactors compute_normalization_factors(const Instance& instance) {
    NormalizationFactors factors;
    factors.max_dist = 0.0f;
    factors.max_tw_diff = 0.0f;
    factors.max_demand = 0.0f;
    factors.max_tw_width = 0.0f;
    factors.max_dist_from_depot = 0.0f;

    for (int i = 1; i <= instance.numCustomers; ++i) {
        factors.max_demand = std::max(factors.max_demand, static_cast<float>(instance.demand[i]));
        factors.max_tw_width = std::max(factors.max_tw_width, instance.TW_Width[i]);
        factors.max_dist_from_depot = std::max(factors.max_dist_from_depot, instance.distanceMatrix[0][i]);

        for (int j = i + 1; j <= instance.numCustomers; ++j) {
            factors.max_dist = std::max(factors.max_dist, instance.distanceMatrix[i][j]);
            factors.max_tw_diff = std::max(factors.max_tw_diff, std::abs(instance.startTW[i] - instance.startTW[j]));
        }
    }
    
    if (factors.max_dist == 0.0f) factors.max_dist = 1.0f;
    if (factors.max_tw_diff == 0.0f) factors.max_tw_diff = 1.0f;
    if (factors.max_demand == 0.0f) factors.max_demand = 1.0f;
    if (factors.max_tw_width == 0.0f) factors.max_tw_width = 1.0f;
    if (factors.max_dist_from_depot == 0.0f) factors.max_dist_from_depot = 1.0f;

    return factors;
}


std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    std::unordered_set<int> removed_customers_set;
    std::vector<int> removed_customers_list;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (instance.numCustomers == 0) {
        return {};
    }
    if (numCustomersToRemove > instance.numCustomers) {
        numCustomersToRemove = instance.numCustomers;
    }

    static NormalizationFactors factors = compute_normalization_factors(instance);

    int seed_customer_idx = getRandomNumber(1, instance.numCustomers);
    removed_customers_set.insert(seed_customer_idx);
    removed_customers_list.push_back(seed_customer_idx);

    while (removed_customers_list.size() < numCustomersToRemove) {
        int ref_customer_idx = removed_customers_list[getRandomNumber(0, removed_customers_list.size() - 1)];

        std::vector<std::pair<float, int>> candidates;
        for (int i = 1; i <= instance.numCustomers; ++i) {
            if (removed_customers_set.find(i) == removed_customers_set.end()) {
                float dist_norm = instance.distanceMatrix[i][ref_customer_idx] / factors.max_dist;
                float tw_diff_norm = std::abs(instance.startTW[i] - instance.startTW[ref_customer_idx]) / factors.max_tw_diff;
                float demand_diff_norm = std::abs(static_cast<float>(instance.demand[i]) - instance.demand[ref_customer_idx]) / factors.max_demand;

                float relatedness_score = W_DIST_SELECT * dist_norm + 
                                          W_TW_SELECT * tw_diff_norm + 
                                          W_DEMAND_SELECT * demand_diff_norm;
                
                candidates.push_back({relatedness_score, i});
            }
        }

        if (candidates.empty()) {
            break;
        }

        std::sort(candidates.begin(), candidates.end());

        int pool_size = std::min(static_cast<int>(candidates.size()), CANDIDATE_POOL_SIZE);
        
        int pick_idx_in_pool = static_cast<int>(std::floor(std::pow(getRandomFractionFast(), ALPHA_SHATTER_PROB) * pool_size));
        
        if (pick_idx_in_pool >= pool_size) {
            pick_idx_in_pool = pool_size - 1;
        }
        
        int next_customer_to_remove = candidates[pick_idx_in_pool].second;
        removed_customers_set.insert(next_customer_to_remove);
        removed_customers_list.push_back(next_customer_to_remove);
    }

    return removed_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    static NormalizationFactors factors = compute_normalization_factors(instance);

    std::vector<std::pair<float, int>> scored_customers;

    for (int customer_id : customers) {
        float tw_tightness_score = 0.0f;
        if (factors.max_tw_width > 0.0f) {
            tw_tightness_score = (factors.max_tw_width - instance.TW_Width[customer_id]) / factors.max_tw_width;
        }
        
        float demand_score = 0.0f;
        if (factors.max_demand > 0.0f) {
            demand_score = static_cast<float>(instance.demand[customer_id]) / factors.max_demand;
        }

        float dist_depot_score = 0.0f;
        if (factors.max_dist_from_depot > 0.0f) {
            dist_depot_score = instance.distanceMatrix[0][customer_id] / factors.max_dist_from_depot;
        }

        float total_score = W_TW_SORT * tw_tightness_score +
                            W_DEMAND_SORT * demand_score +
                            W_DIST_DEPOT_SORT * dist_depot_score;
        
        total_score += getRandomFraction(-RANDOM_NOISE_SORT, RANDOM_NOISE_SORT) * total_score;

        scored_customers.push_back({total_score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}