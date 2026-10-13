#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    const Instance& instance = sol.instance;

    int minCustomersToRemove = static_cast<int>(instance.numCustomers * 0.03);
    int maxCustomersToRemove = static_cast<int>(instance.numCustomers * 0.06);
    if (minCustomersToRemove < 10) minCustomersToRemove = 10; 
    if (maxCustomersToRemove < minCustomersToRemove + 5) maxCustomersToRemove = minCustomersToRemove + 5; 
    
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int seedCustomer = getRandomNumber(1, instance.numCustomers); 
        
        selectedCustomersSet.insert(seedCustomer);

        if (selectedCustomersSet.size() >= numCustomersToRemove) break;

        int tourIdx = sol.customerToTourMap[seedCustomer - 1]; 
        
        if (tourIdx >= 0 && tourIdx < sol.tours.size()) {
            const Tour& tour = sol.tours[tourIdx];
            if (!tour.customers.empty()) {
                int numToAddFromTour = getRandomNumber(1, 3); 
                for (int i = 0; i < numToAddFromTour && selectedCustomersSet.size() < numCustomersToRemove; ++i) {
                    int tourCustomerIdx = getRandomNumber(0, tour.customers.size() - 1);
                    selectedCustomersSet.insert(tour.customers[tourCustomerIdx]); 
                }
            }
        }

        if (selectedCustomersSet.size() >= numCustomersToRemove) break;

        if (!instance.adj[seedCustomer].empty()) { 
            int numNeighborsToConsider = std::min((int)instance.adj[seedCustomer].size(), getRandomNumber(3, 7)); 
            
            for (int i = 0; i < numNeighborsToConsider && selectedCustomersSet.size() < numCustomersToRemove; ++i) {
                int neighborNodeId = instance.adj[seedCustomer][i];
                if (neighborNodeId != 0 && neighborNodeId <= instance.numCustomers) { 
                    selectedCustomersSet.insert(neighborNodeId); 
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    double max_demand_overall = 1.0; 
    for (int i = 1; i <= instance.numCustomers; ++i) { 
        if (instance.demand[i] > max_demand_overall) {
            max_demand_overall = instance.demand[i];
        }
    }

    float max_dist_depot_overall = 1.0f; 
    for (int i = 1; i <= instance.numCustomers; ++i) { 
        if (instance.distanceMatrix[0][i] > max_dist_depot_overall) {
            max_dist_depot_overall = instance.distanceMatrix[0][i];
        }
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    const float weight_demand_normalized = 2.0f; 
    const float weight_distance_normalized = 1.0f; 
    const float weight_stochastic_normalized = 0.5f; 

    for (int customer_id : customers) {
        float normalized_demand = static_cast<float>(instance.demand[customer_id]) / max_demand_overall;
        float normalized_dist_depot = instance.distanceMatrix[0][customer_id] / max_dist_depot_overall;
        
        float score = (normalized_demand * weight_demand_normalized) + 
                      (normalized_dist_depot * weight_distance_normalized) + 
                      (getRandomFractionFast() * weight_stochastic_normalized);
        
        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}