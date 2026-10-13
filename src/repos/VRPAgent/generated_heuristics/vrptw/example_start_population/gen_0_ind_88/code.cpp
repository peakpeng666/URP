#include "AgentDesigned.h"
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <limits>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomersTotal = sol.instance.numCustomers;
    int min_remove = 10;
    int max_remove = 30;

    if (numCustomersTotal < 50) {
        min_remove = std::max(1, numCustomersTotal / 5);
        max_remove = std::max(min_remove + 1, numCustomersTotal / 3);
    }
    min_remove = std::min(min_remove, numCustomersTotal);
    max_remove = std::min(max_remove, numCustomersTotal);

    int numCustomersToRemove = getRandomNumber(min_remove, max_remove);

    if (numCustomersToRemove <= 0) {
        return {};
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersVec.push_back(seedCustomer);

    int expansionAttempts = 0;
    const int MAX_EXPANSION_ATTEMPTS = numCustomersToRemove * 5;

    while (selectedCustomersSet.size() < numCustomersToRemove && expansionAttempts < MAX_EXPANSION_ATTEMPTS) {
        int parentIdx = getRandomNumber(0, selectedCustomersVec.size() - 1);
        int parentCustomer = selectedCustomersVec[parentIdx];

        bool customerAddedInThisAttempt = false;
        const int MAX_ADJ_NEIGHBORS_TO_CONSIDER = 10;
        int neighborsConsidered = 0;

        for (int neighbor : sol.instance.adj[parentCustomer]) {
            if (neighbor == 0) continue;
            if (neighborsConsidered >= MAX_ADJ_NEIGHBORS_TO_CONSIDER) break;

            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (getRandomFractionFast() < 0.7) {
                    selectedCustomersSet.insert(neighbor);
                    selectedCustomersVec.push_back(neighbor);
                    customerAddedInThisAttempt = true;
                    break;
                }
            }
            neighborsConsidered++;
            if (selectedCustomersSet.size() >= numCustomersToRemove) break;
        }

        if (!customerAddedInThisAttempt) {
            int newSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.find(newSeedCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(newSeedCustomer);
                selectedCustomersVec.push_back(newSeedCustomer);
            }
        }
        expansionAttempts++;
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    const float WEIGHT_TW_TIGHTNESS = 0.5f;
    const float WEIGHT_DEMAND = 0.3f;
    const float WEIGHT_SERVICE_TIME = 0.2f;
    const float STOCHASTICITY_FACTOR = 0.4f;

    float max_base_score_observed = 0.0f;
    float min_base_score_observed = std::numeric_limits<float>::max();

    for (int customer_id : customers) {
        float tw_tightness_val = (instance.TW_Width[customer_id] > 0.001f) ? (1.0f / instance.TW_Width[customer_id]) : 1000.0f;
        float demand_val = static_cast<float>(instance.demand[customer_id]);
        float service_time_val = instance.serviceTime[customer_id];

        float current_base_score = (tw_tightness_val * WEIGHT_TW_TIGHTNESS) +
                                   (demand_val * WEIGHT_DEMAND) +
                                   (service_time_val * WEIGHT_SERVICE_TIME);
        
        if (current_base_score > max_base_score_observed) max_base_score_observed = current_base_score;
        if (current_base_score < min_base_score_observed) min_base_score_observed = current_base_score;
    }

    float score_range = max_base_score_observed - min_base_score_observed;
    if (score_range < 0.001f) {
        score_range = 10.0f;
    }

    for (int customer_id : customers) {
        float tw_tightness_val = (instance.TW_Width[customer_id] > 0.001f) ? (1.0f / instance.TW_Width[customer_id]) : 1000.0f;
        float demand_val = static_cast<float>(instance.demand[customer_id]);
        float service_time_val = instance.serviceTime[customer_id];

        float base_score = (tw_tightness_val * WEIGHT_TW_TIGHTNESS) +
                           (demand_val * WEIGHT_DEMAND) +
                           (service_time_val * WEIGHT_SERVICE_TIME);

        float random_noise = (getRandomFractionFast() * 2.0f - 1.0f) * score_range * STOCHASTICITY_FACTOR;
        
        float final_score = base_score + random_noise;
        scored_customers.push_back({final_score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}