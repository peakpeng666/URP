#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits>
#include "Utils.h"


std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 20;
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int numTotalCustomers = sol.instance.numCustomers;
    if (numTotalCustomers == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, numTotalCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    selectedCustomersVec.push_back(initialSeedCustomer);

    int maxTotalExpansionAttempts = numCustomersToRemove * 50; 
    int currentTotalAttempts = 0;

    while (selectedCustomersSet.size() < numCustomersToRemove && currentTotalAttempts < maxTotalExpansionAttempts) {
        int pivotCustomerIndex = getRandomNumber(0, (int)selectedCustomersVec.size() - 1);
        int pivotCustomer = selectedCustomersVec[pivotCustomerIndex];

        std::vector<int> potentialNewCustomers;
        int numNeighborsToCheck = std::min((int)sol.instance.adj[pivotCustomer].size(), 15); 

        for (int i = 0; i < numNeighborsToCheck; ++i) {
            int neighbor = sol.instance.adj[pivotCustomer][i];
            if (neighbor != 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                potentialNewCustomers.push_back(neighbor);
            }
        }

        if (!potentialNewCustomers.empty()) {
            int chosenCustomer = potentialNewCustomers[getRandomNumber(0, (int)potentialNewCustomers.size() - 1)];
            selectedCustomersSet.insert(chosenCustomer);
            selectedCustomersVec.push_back(chosenCustomer);
        }
        currentTotalAttempts++;
    }

    return selectedCustomersVec;
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float max_tw_width = 0.0f;
    float max_start_tw = 0.0f;
    float max_demand = 0.0f;
    float max_service_time = 0.0f;

    for (int i = 1; i <= instance.numCustomers; ++i) {
        max_tw_width = std::max(max_tw_width, instance.TW_Width[i]);
        max_start_tw = std::max(max_start_tw, instance.startTW[i]);
        max_demand = std::max(max_demand, (float)instance.demand[i]);
        max_service_time = std::max(max_service_time, instance.serviceTime[i]);
    }
    
    if (max_tw_width == 0.0f) max_tw_width = 1.0f; 
    if (max_start_tw == 0.0f) max_start_tw = 1.0f;
    if (max_demand == 0.0f) max_demand = 1.0f;
    if (max_service_time == 0.0f) max_service_time = 1.0f;

    const float NOISE_MAGNITUDE = 0.001f;

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = 0.0f;
        
        score += (max_tw_width - instance.TW_Width[customer_id]) / max_tw_width;
        score += (max_start_tw - instance.startTW[customer_id]) / max_start_tw;
        score += instance.demand[customer_id] / max_demand;
        score += instance.serviceTime[customer_id] / max_service_time;
        
        score += getRandomFraction(-NOISE_MAGNITUDE, NOISE_MAGNITUDE);

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}