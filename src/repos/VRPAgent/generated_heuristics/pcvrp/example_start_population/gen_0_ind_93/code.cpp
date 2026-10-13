#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort

// Helper for select_by_llm_1: Fisher-Yates shuffle for small vectors
template<typename T>
void shuffle_vector_in_place(std::vector<T>& vec) {
    if (vec.empty()) {
        return;
    }
    for (int i = 0; i < static_cast<int>(vec.size()) - 1; ++i) {
        int j = getRandomNumber(i, static_cast<int>(vec.size()) - 1);
        if (i != j) {
            std::swap(vec[i], vec[j]);
        }
    }
}

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomersToRemove = getRandomNumber(15, 30); 
    
    std::vector<int> frontierCustomers;

    std::vector<int> all_customer_ids(sol.instance.numCustomers);
    for (int i = 0; i < sol.instance.numCustomers; ++i) {
        all_customer_ids[i] = i + 1;
    }
    shuffle_vector_in_place(all_customer_ids);

    int current_all_customers_idx = 0;

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (frontierCustomers.empty()) {
            int seed_customer_id = -1;
            while (current_all_customers_idx < all_customer_ids.size()) {
                int potential_seed = all_customer_ids[current_all_customers_idx++];
                if (selectedCustomersSet.find(potential_seed) == selectedCustomersSet.end()) {
                    seed_customer_id = potential_seed;
                    break;
                }
            }

            if (seed_customer_id == -1) {
                break;
            }

            selectedCustomersSet.insert(seed_customer_id);
            selectedCustomersVec.push_back(seed_customer_id);
            if (selectedCustomersSet.size() == numCustomersToRemove) break;

            frontierCustomers.push_back(seed_customer_id);
        }

        int frontier_idx = getRandomNumber(0, static_cast<int>(frontierCustomers.size()) - 1);
        int current_expansion_point = frontierCustomers[frontier_idx];
        
        std::swap(frontierCustomers[frontier_idx], frontierCustomers.back());
        frontierCustomers.pop_back();

        for (int neighbor_id : sol.instance.adj[current_expansion_point]) {
            if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(neighbor_id);
                selectedCustomersVec.push_back(neighbor_id);
                if (selectedCustomersSet.size() == numCustomersToRemove) break;

                frontierCustomers.push_back(neighbor_id);
            }
        }
        if (selectedCustomersSet.size() == numCustomersToRemove) break;
    }

    return selectedCustomersVec;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id];
        score -= instance.demand[customer_id] * 0.5f;
        
        score += getRandomFraction() * 0.1f * instance.prizes[customer_id]; 

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}