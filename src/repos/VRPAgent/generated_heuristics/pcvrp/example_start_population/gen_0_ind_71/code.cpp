#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> selectedCustomers_list;
    
    std::vector<int> currentCandidates_vector; 
    std::unordered_set<int> currentCandidates_set; 

    int numCustomersToRemove = getRandomNumber(15, 30); 
    int numCustomers = sol.instance.numCustomers;

    int seedCustomer = getRandomNumber(1, numCustomers);
    selectedCustomers_set.insert(seedCustomer);
    selectedCustomers_list.push_back(seedCustomer);

    if (selectedCustomers_list.size() >= numCustomersToRemove) {
        return selectedCustomers_list;
    }

    for (int neighbor_c : sol.instance.adj[seedCustomer]) {
        if (neighbor_c == 0) continue;
        if (selectedCustomers_set.count(neighbor_c) == 0) {
            if (currentCandidates_set.count(neighbor_c) == 0) {
                currentCandidates_vector.push_back(neighbor_c);
                currentCandidates_set.insert(neighbor_c);
            }
        }
    }

    while (selectedCustomers_list.size() < numCustomersToRemove && !currentCandidates_vector.empty()) {
        int rand_idx = getRandomNumber(0, currentCandidates_vector.size() - 1);
        int customerToSelect = currentCandidates_vector[rand_idx];

        currentCandidates_vector[rand_idx] = currentCandidates_vector.back();
        currentCandidates_vector.pop_back();
        currentCandidates_set.erase(customerToSelect);

        selectedCustomers_set.insert(customerToSelect);
        selectedCustomers_list.push_back(customerToSelect);

        if (selectedCustomers_list.size() >= numCustomersToRemove) {
            break;
        }

        for (int neighbor_c : sol.instance.adj[customerToSelect]) {
            if (neighbor_c == 0) continue;
            if (selectedCustomers_set.count(neighbor_c) == 0) {
                if (currentCandidates_set.count(neighbor_c) == 0) {
                    currentCandidates_vector.push_back(neighbor_c);
                    currentCandidates_set.insert(neighbor_c);
                }
            }
        }
    }
    
    while (selectedCustomers_list.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, numCustomers);
        if (selectedCustomers_set.count(randomCustomer) == 0) {
            selectedCustomers_set.insert(randomCustomer);
            selectedCustomers_list.push_back(randomCustomer);
        }
    }

    return selectedCustomers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<int, float>> customerScores;
    customerScores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id];
        score += getRandomFractionFast() * 0.01;
        
        customerScores.push_back({customer_id, score});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.second > b.second;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].first;
    }
}