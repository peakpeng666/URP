#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector> // For std::vector
#include <utility> // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomers = sol.instance.numCustomers;
    
    int minCustomersToRemove = 5;
    int maxCustomersToRemove = 15;
    int numCustomersToSelect = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToSelect == 0) return {};

    int current_customer = getRandomNumber(1, numCustomers);
    selectedCustomers.insert(current_customer);
    
    int numNeighborsToConsider = getRandomNumber(3, 8);

    while (selectedCustomers.size() < numCustomersToSelect) {
        std::vector<int> potential_next_customers;

        if (sol.instance.adj.size() > current_customer && !sol.instance.adj[current_customer].empty()) {
            int neighbors_count = 0;
            for (int neighbor : sol.instance.adj[current_customer]) {
                if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    potential_next_customers.push_back(neighbor);
                }
                neighbors_count++;
                if (neighbors_count >= numNeighborsToConsider) break;
            }
        }
        
        bool jumpToNewSeed = (getRandomFraction() < 0.15f) || potential_next_customers.empty();
        
        if (jumpToNewSeed) {
            current_customer = getRandomNumber(1, numCustomers);
            if (selectedCustomers.find(current_customer) == selectedCustomers.end()) {
                selectedCustomers.insert(current_customer);
            }
        } else {
            if (!potential_next_customers.empty()) {
                current_customer = potential_next_customers[getRandomNumber(0, static_cast<int>(potential_next_customers.size()) - 1)];
                selectedCustomers.insert(current_customer);
            } else {
                current_customer = getRandomNumber(1, numCustomers);
                selectedCustomers.insert(current_customer);
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) return;

    std::vector<std::pair<float, int>> customer_values;
    customer_values.reserve(customers.size());

    float choice = getRandomFraction(); 
    float noise_magnitude = 0.01f;

    if (choice < 0.5f) {
        for (int customer_id : customers) {
            float value = instance.TW_Width[customer_id];
            float noise = getRandomFraction(-noise_magnitude, noise_magnitude) * value;
            customer_values.push_back({value + noise, customer_id});
        }
        std::sort(customer_values.begin(), customer_values.end());
    } else {
        for (int customer_id : customers) {
            float value = instance.startTW[customer_id];
            float noise = getRandomFraction(-noise_magnitude, noise_magnitude) * value;
            customer_values.push_back({value + noise, customer_id});
        }
        std::sort(customer_values.begin(), customer_values.end());
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_values[i].second;
    }
}