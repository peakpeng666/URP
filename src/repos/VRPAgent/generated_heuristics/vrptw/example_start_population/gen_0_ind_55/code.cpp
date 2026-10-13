#include "AgentDesigned.h"
#include <vector>
#include <unordered_set>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 30);

    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> selectedCustomers_vec;

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers_set.insert(seed_customer);
    selectedCustomers_vec.push_back(seed_customer);

    while (selectedCustomers_set.size() < numCustomersToRemove) {
        int pivot_idx = getRandomNumber(0, selectedCustomers_vec.size() - 1);
        int pivot_customer = selectedCustomers_vec[pivot_idx];

        std::vector<int> potential_adds;
        const int search_depth = 10; 
        for (int i = 0; i < sol.instance.adj[pivot_customer].size() && i < search_depth; ++i) {
            int neighbor_id = sol.instance.adj[pivot_customer][i];
            if (neighbor_id != 0 && selectedCustomers_set.find(neighbor_id) == selectedCustomers_set.end()) {
                potential_adds.push_back(neighbor_id);
            }
        }

        int customer_to_add = -1;
        if (!potential_adds.empty()) {
            int chosen_idx = getRandomNumber(0, potential_adds.size() - 1);
            customer_to_add = potential_adds[chosen_idx];
        } else {
            customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers_set.find(customer_to_add) != selectedCustomers_set.end()) {
                customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
            }
        }
        
        selectedCustomers_set.insert(customer_to_add);
        selectedCustomers_vec.push_back(customer_to_add);
    }

    return selectedCustomers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;

    for (int customer_id : customers) {
        float score = instance.TW_Width[customer_id]; 
        score *= (1.0 + getRandomFraction(-0.1, 0.1));

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first < b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}