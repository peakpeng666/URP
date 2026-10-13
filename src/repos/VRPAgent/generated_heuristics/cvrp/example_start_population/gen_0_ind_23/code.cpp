#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selectedCustomersVec;
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateCustomersVec;
    std::unordered_set<int> candidateCustomersSet;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove == 0 || sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersVec.push_back(initial_customer_id);
    selectedCustomersSet.insert(initial_customer_id);

    for (int neighbor_id : sol.instance.adj[initial_customer_id]) {
        if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers) {
            if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end() &&
                candidateCustomersSet.find(neighbor_id) == candidateCustomersSet.end()) {
                candidateCustomersVec.push_back(neighbor_id);
                candidateCustomersSet.insert(neighbor_id);
            }
        }
    }

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        int next_customer_to_add = -1;

        if (!candidateCustomersVec.empty()) {
            int idx = getRandomNumber(0, candidateCustomersVec.size() - 1);
            next_customer_to_add = candidateCustomersVec[idx];
            
            candidateCustomersSet.erase(next_customer_to_add);
            candidateCustomersVec[idx] = candidateCustomersVec.back();
            candidateCustomersVec.pop_back();

        } else {
            int current_customer_count = sol.instance.numCustomers;
            bool found_unselected = false;
            for (int attempt = 0; attempt < current_customer_count * 2 && selectedCustomersSet.size() < sol.instance.numCustomers; ++attempt) { 
                int potential_customer_id = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(potential_customer_id) == selectedCustomersSet.end()) {
                    next_customer_to_add = potential_customer_id;
                    found_unselected = true;
                    break;
                }
            }
            if (!found_unselected) { 
                 break;
            }
        }

        if (next_customer_to_add != -1 && selectedCustomersSet.find(next_customer_to_add) == selectedCustomersSet.end()) {
            selectedCustomersVec.push_back(next_customer_to_add);
            selectedCustomersSet.insert(next_customer_to_add);

            for (int neighbor_id : sol.instance.adj[next_customer_to_add]) {
                if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers) {
                    if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end() &&
                        candidateCustomersSet.find(neighbor_id) == candidateCustomersSet.end()) {
                        candidateCustomersVec.push_back(neighbor_id);
                        candidateCustomersSet.insert(neighbor_id);
                    }
                }
            }
        }
    }
    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_metrics;
    customer_metrics.reserve(customers.size());

    float max_dist = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) { 
        if (instance.distanceMatrix[0][i] > max_dist) {
            max_dist = instance.distanceMatrix[0][i];
        }
    }
    
    const float NOISE_SCALE = (max_dist > 0.0f) ? 0.05f * max_dist : 1.0f; 

    for (int customer_id : customers) {
        float distance_from_depot = instance.distanceMatrix[0][customer_id];
        float perturbed_metric = distance_from_depot + getRandomFractionFast() * NOISE_SCALE;
        customer_metrics.push_back({perturbed_metric, customer_id});
    }

    std::sort(customer_metrics.begin(), customer_metrics.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; 
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_metrics[i].second;
    }
}