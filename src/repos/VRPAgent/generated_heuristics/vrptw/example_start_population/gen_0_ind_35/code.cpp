#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::min, std::sort
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    const int num_customers_to_remove = getRandomNumber(10, 30);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_seed);
    selectedCustomersVec.push_back(initial_seed);

    while (selectedCustomersSet.size() < num_customers_to_remove) {
        bool customer_added_this_iteration = false;

        if (getRandomFractionFast() < 0.15 && sol.instance.numCustomers > selectedCustomersSet.size()) {
            int random_customer = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            while (selectedCustomersSet.count(random_customer) && attempts < 100) {
                random_customer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (!selectedCustomersSet.count(random_customer)) {
                selectedCustomersSet.insert(random_customer);
                selectedCustomersVec.push_back(random_customer);
                customer_added_this_iteration = true;
            }
        }

        if (!customer_added_this_iteration) {
            if (selectedCustomersVec.empty()) {
                if (sol.instance.numCustomers > selectedCustomersSet.size()) {
                    int fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
                    int attempts = 0;
                    while (selectedCustomersSet.count(fallback_customer) && attempts < 1000) {
                        fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
                        attempts++;
                    }
                    if (!selectedCustomersSet.count(fallback_customer)) {
                        selectedCustomersSet.insert(fallback_customer);
                        selectedCustomersVec.push_back(fallback_customer);
                        customer_added_this_iteration = true;
                    }
                } else {
                    break;
                }
            } else {
                int pivot_index = getRandomNumber(0, selectedCustomersVec.size() - 1);
                int pivot_customer_id = selectedCustomersVec[pivot_index];

                const auto& neighbors = sol.instance.adj[pivot_customer_id];
                
                std::vector<int> unselected_neighbors_candidates;
                const int num_neighbors_to_check = std::min((int)neighbors.size(), 10);

                for (int i = 0; i < num_neighbors_to_check; ++i) {
                    int neighbor_id = neighbors[i];
                    if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers && !selectedCustomersSet.count(neighbor_id)) {
                        unselected_neighbors_candidates.push_back(neighbor_id);
                    }
                }

                if (!unselected_neighbors_candidates.empty()) {
                    int chosen_neighbor = unselected_neighbors_candidates[getRandomNumber(0, unselected_neighbors_candidates.size() - 1)];
                    selectedCustomersSet.insert(chosen_neighbor);
                    selectedCustomersVec.push_back(chosen_neighbor);
                    customer_added_this_iteration = true;
                }
            }
        }

        if (!customer_added_this_iteration && sol.instance.numCustomers > selectedCustomersSet.size()) {
            int fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            while (selectedCustomersSet.count(fallback_customer) && attempts < 1000) {
                fallback_customer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (!selectedCustomersSet.count(fallback_customer)) {
                selectedCustomersSet.insert(fallback_customer);
                selectedCustomersVec.push_back(fallback_customer);
            } else {
                break;
            }
        }
    }
    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float max_tw_width = 0.0f;
    float max_service_time = 0.0f;
    float max_demand = 0.0f;

    for (int customer_id : customers) {
        max_tw_width = std::max(max_tw_width, instance.TW_Width[customer_id]);
        max_service_time = std::max(max_service_time, instance.serviceTime[customer_id]);
        max_demand = std::max(max_demand, (float)instance.demand[customer_id]);
    }

    if (max_tw_width == 0) max_tw_width = 1.0f;
    if (max_service_time == 0) max_service_time = 1.0f;
    if (max_demand == 0) max_demand = 1.0f;

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    const float W_TW = 0.5f;
    const float W_SERVICE = 0.3f;
    const float W_DEMAND = 0.2f;
    const float STOCHASTIC_PERTURBATION_RANGE = 0.05f;

    for (int customer_id : customers) {
        float normalized_tw = instance.TW_Width[customer_id] / max_tw_width;
        float normalized_service = instance.serviceTime[customer_id] / max_service_time;
        float normalized_demand = (float)instance.demand[customer_id] / max_demand;

        float difficulty_score = (1.0f - normalized_tw) * W_TW +
                                normalized_service * W_SERVICE +
                                normalized_demand * W_DEMAND;

        difficulty_score += getRandomFraction(-STOCHASTIC_PERTURBATION_RANGE, STOCHASTIC_PERTURBATION_RANGE);

        customer_scores.push_back({difficulty_score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}