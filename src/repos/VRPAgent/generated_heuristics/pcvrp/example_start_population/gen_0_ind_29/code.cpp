#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <cmath>

#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec; 

    int numCustomersToRemove = getRandomNumber(10, 25); 

    int seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seed_customer_id);
    selectedCustomersVec.push_back(seed_customer_id);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool customer_added_in_round = false;
        
        for (int attempts = 0; attempts < 5 && !customer_added_in_round; ++attempts) {
            int random_source_idx = getRandomNumber(0, selectedCustomersVec.size() - 1);
            int source_customer = selectedCustomersVec[random_source_idx];

            for (int neighbor_idx = 0; neighbor_idx < sol.instance.adj[source_customer].size(); ++neighbor_idx) {
                int neighbor_id = sol.instance.adj[source_customer][neighbor_idx];

                if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                    if (getRandomFractionFast() < 0.75) { 
                        selectedCustomersSet.insert(neighbor_id);
                        selectedCustomersVec.push_back(neighbor_id);
                        customer_added_in_round = true;
                        break; 
                    }
                }
            }
        }

        if (!customer_added_in_round || getRandomFractionFast() < 0.1) { 
            int random_customer_id = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.find(random_customer_id) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(random_customer_id);
                selectedCustomersVec.push_back(random_customer_id);
            }
        }
    }

    return selectedCustomersVec;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size()); 

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id];
        
        float effective_dist = dist_to_depot + 1e-6f; 

        int degree = instance.adj[customer_id].size(); 

        float score = (prize / effective_dist) + (0.05f * degree);

        score += getRandomFractionFast() * 0.01f; 

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}