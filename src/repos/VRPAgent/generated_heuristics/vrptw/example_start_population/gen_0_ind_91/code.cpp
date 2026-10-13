#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int min_remove = 10;
    int max_remove = 20;
    
    int num_customers_in_instance = sol.instance.numCustomers;
    if (max_remove > num_customers_in_instance) {
        max_remove = num_customers_in_instance;
    }
    if (min_remove > max_remove) {
        min_remove = max_remove;
    }
    
    int numCustomersToRemove = getRandomNumber(min_remove, max_remove);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int currentCustomer = getRandomNumber(1, num_customers_in_instance);
    selectedCustomersSet.insert(currentCustomer);
    selectedCustomersList.push_back(currentCustomer);

    static thread_local std::mt19937 gen(std::random_device{}());

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool added_customer_in_iteration = false;
        
        std::vector<int> current_selected_customers_copy = selectedCustomersList;
        std::shuffle(current_selected_customers_copy.begin(), current_selected_customers_copy.end(), gen);

        for (int source_node : current_selected_customers_copy) {
            for (int neighbor_node : sol.instance.adj[source_node]) {
                if (neighbor_node == 0) continue; 
                if (selectedCustomersSet.count(neighbor_node)) continue;

                selectedCustomersSet.insert(neighbor_node);
                selectedCustomersList.push_back(neighbor_node);
                added_customer_in_iteration = true;
                break; 
            }
            if (selectedCustomersSet.size() >= numCustomersToRemove) break;
        }

        if (!added_customer_in_iteration && selectedCustomersSet.size() < numCustomersToRemove) {
            int random_unselected_customer = -1;
            int counter = 0;
            int max_tries = num_customers_in_instance * 2; 
            while (counter < max_tries) {
                int candidate = getRandomNumber(1, num_customers_in_instance);
                if (!selectedCustomersSet.count(candidate)) {
                    random_unselected_customer = candidate;
                    break;
                }
                counter++;
            }

            if (random_unselected_customer != -1) {
                selectedCustomersSet.insert(random_unselected_customer);
                selectedCustomersList.push_back(random_unselected_customer);
            } else {
                break; 
            }
        }
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    float w_tw = getRandomFraction(0.0f, 1.0f);
    float w_demand = getRandomFraction(0.0f, 1.0f);
    float w_service = getRandomFraction(0.0f, 1.0f);

    float sum_weights = w_tw + w_demand + w_service;
    if (sum_weights < 1e-6f) {
        w_tw = 1.0f; w_demand = 0.0f; w_service = 0.0f;
        sum_weights = 1.0f;
    }
    w_tw /= sum_weights;
    w_demand /= sum_weights;
    w_service /= sum_weights;

    float max_tw_width = 0.0f;
    float max_service_time = 0.0f;

    for (int cust_idx : customers) {
        if (instance.TW_Width[cust_idx] > max_tw_width) max_tw_width = instance.TW_Width[cust_idx];
        if (instance.serviceTime[cust_idx] > max_service_time) max_service_time = instance.serviceTime[cust_idx];
    }
    
    if (max_tw_width == 0.0f) max_tw_width = 1.0f;
    if (max_service_time == 0.0f) max_service_time = 1.0f;

    for (int cust_idx : customers) {
        float normalized_tw = instance.TW_Width[cust_idx] / max_tw_width;
        float normalized_demand = static_cast<float>(instance.demand[cust_idx]) / instance.vehicleCapacity;
        float normalized_service = instance.serviceTime[cust_idx] / max_service_time;

        float score = w_tw * (1.0f - normalized_tw) + 
                      w_demand * normalized_demand +
                      w_service * normalized_service;

        score += getRandomFraction(-0.001f, 0.001f); 

        customerScores.push_back({score, cust_idx});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}