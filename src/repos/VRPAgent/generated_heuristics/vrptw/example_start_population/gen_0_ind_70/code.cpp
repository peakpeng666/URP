#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <queue>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::queue<int> customersToExplore;

    int numCustomersToRemove = getRandomNumber(10, 20);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    
    const int max_neighbors_to_consider = 10;
    const float selection_prob_for_neighbor = 0.8f;
    const float jump_prob = 0.1f;

    int first_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(first_customer_idx);
    customersToExplore.push(first_customer_idx);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool expanded_from_existing = false;
        if (!customersToExplore.empty() && getRandomFractionFast() > jump_prob) {
            int current_customer = customersToExplore.front();
            customersToExplore.pop();
            
            for (size_t i = 0; i < sol.instance.adj[current_customer].size(); ++i) {
                int neighbor = sol.instance.adj[current_customer][i];

                if (neighbor == 0) continue;
                if (selectedCustomersSet.count(neighbor)) continue;

                if (i >= max_neighbors_to_consider) break; 

                if (getRandomFractionFast() < selection_prob_for_neighbor) {
                    selectedCustomersSet.insert(neighbor);
                    customersToExplore.push(neighbor);
                    expanded_from_existing = true;
                    if (selectedCustomersSet.size() >= numCustomersToRemove) break;
                }
            }
        }
        
        if (!expanded_from_existing || getRandomFractionFast() < jump_prob) {
            int random_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.find(random_customer_idx) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(random_customer_idx);
                customersToExplore.push(random_customer_idx);
            }
        }

        if (customersToExplore.empty() && selectedCustomersSet.size() < numCustomersToRemove) {
            int random_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.find(random_customer_idx) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(random_customer_idx);
                customersToExplore.push(random_customer_idx);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    float min_tw_width = instance.TW_Width[customers[0]];
    float max_tw_width = instance.TW_Width[customers[0]];
    float max_demand = static_cast<float>(instance.demand[customers[0]]);
    float max_dist_from_depot = instance.distanceMatrix[0][customers[0]];
    float max_service_time = instance.serviceTime[customers[0]];

    for (int customer_id : customers) {
        min_tw_width = std::min(min_tw_width, instance.TW_Width[customer_id]);
        max_tw_width = std::max(max_tw_width, instance.TW_Width[customer_id]);
        max_demand = std::max(max_demand, static_cast<float>(instance.demand[customer_id]));
        max_dist_from_depot = std::max(max_dist_from_depot, instance.distanceMatrix[0][customer_id]);
        max_service_time = std::max(max_service_time, instance.serviceTime[customer_id]);
    }

    float w_tw = 0.45f + (getRandomFractionFast() - 0.5f) * 0.1f;
    float w_demand = 0.30f + (getRandomFractionFast() - 0.5f) * 0.1f;
    float w_dist_depot = 0.15f + (getRandomFractionFast() - 0.5f) * 0.05f;
    float w_service_time = 0.10f + (getRandomFractionFast() - 0.5f) * 0.05f;

    float total_weights = w_tw + w_demand + w_dist_depot + w_service_time;
    w_tw /= total_weights;
    w_demand /= total_weights;
    w_dist_depot /= total_weights;
    w_service_time /= total_weights;

    for (int customer_id : customers) {
        float current_tw_width = instance.TW_Width[customer_id];
        float current_demand = static_cast<float>(instance.demand[customer_id]);
        float current_dist_from_depot = instance.distanceMatrix[0][customer_id];
        float current_service_time = instance.serviceTime[customer_id];

        float normalized_tw_tightness = 0.0f;
        if (max_tw_width != min_tw_width) {
            normalized_tw_tightness = 1.0f - ((current_tw_width - min_tw_width) / (max_tw_width - min_tw_width));
        } else {
            normalized_tw_tightness = 0.5f;
        }
        
        float normalized_demand = (max_demand > 0) ? (current_demand / max_demand) : 0.0f;
        float normalized_dist_from_depot = (max_dist_from_depot > 0) ? (current_dist_from_depot / max_dist_from_depot) : 0.0f;
        float normalized_service_time = (max_service_time > 0) ? (current_service_time / max_service_time) : 0.0f;

        float score = w_tw * normalized_tw_tightness +
                      w_demand * normalized_demand +
                      w_dist_depot * normalized_dist_from_depot +
                      w_service_time * normalized_service_time;

        score += getRandomFractionFast() * 0.001f;

        customer_scores.emplace_back(score, customer_id);
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}