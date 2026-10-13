#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove <= 0) {
        return {};
    }

    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initial_customer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> potential_next_customers;
        
        for (int sel_cust : selectedCustomers) {
            int num_neighbors_to_consider = std::min((int)sol.instance.adj[sel_cust].size(), 10); 
            for (int i = 0; i < num_neighbors_to_consider; ++i) {
                int neighbor_cust = sol.instance.adj[sel_cust][i];
                if (neighbor_cust >= 1 && neighbor_cust <= sol.instance.numCustomers && 
                    selectedCustomers.find(neighbor_cust) == selectedCustomers.end()) {
                    potential_next_customers.push_back(neighbor_cust);
                }
            }
        }

        if (!potential_next_customers.empty()) {
            int idx = getRandomNumber(0, potential_next_customers.size() - 1);
            selectedCustomers.insert(potential_next_customers[idx]);
        } else {
            int random_unselected_customer;
            int safety_counter = 0;
            do {
                random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
                safety_counter++;
                if (safety_counter > sol.instance.numCustomers * 2) { 
                    break;
                }
            } while (selectedCustomers.find(random_unselected_customer) != selectedCustomers.end());
            
            if (selectedCustomers.find(random_unselected_customer) == selectedCustomers.end()) {
                selectedCustomers.insert(random_unselected_customer);
            } else {
                 break;
            }
        }
    }
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id];

        float score = prize * 1000.0f - dist_to_depot + getRandomFraction() * 50.0f;
        
        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.rbegin(), customer_scores.rend());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}