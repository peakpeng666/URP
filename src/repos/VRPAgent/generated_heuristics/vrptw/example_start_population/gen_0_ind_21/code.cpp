#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::shuffle
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // Assumed to provide getRandomNumber, getRandomFraction, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_list; 
    
    int num_to_remove = getRandomNumber(10, 30); 
    
    std::vector<int> expansion_front; 

    // 1. Initial Seed Selection
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers); 
    selected_customers_set.insert(seed_customer);
    selected_customers_list.push_back(seed_customer);
    expansion_front.push_back(seed_customer);

    // 2. Iterative Expansion
    while (selected_customers_list.size() < num_to_remove) {
        if (expansion_front.empty()) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            const int max_attempts = sol.instance.numCustomers * 2; 
            while (selected_customers_set.count(new_seed) && attempts < max_attempts) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (attempts >= max_attempts) { 
                break; 
            }
            selected_customers_set.insert(new_seed);
            selected_customers_list.push_back(new_seed);
            expansion_front.push_back(new_seed);
            if (selected_customers_list.size() == num_to_remove) break; 
        }

        int pivot_idx = getRandomNumber(0, expansion_front.size() - 1);
        int pivot_customer = expansion_front[pivot_idx];

        std::swap(expansion_front[pivot_idx], expansion_front.back());
        expansion_front.pop_back();

        std::vector<int> potential_adds;
        int num_neighbors_to_check = std::min((int)sol.instance.adj[pivot_customer].size(), 10); 

        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor = sol.instance.adj[pivot_customer][i];
            if (selected_customers_set.find(neighbor) == selected_customers_set.end()) { 
                potential_adds.push_back(neighbor);
            }
        }

        if (!potential_adds.empty()) {
            int customer_to_add = potential_adds[getRandomNumber(0, potential_adds.size() - 1)];
            
            selected_customers_set.insert(customer_to_add);
            selected_customers_list.push_back(customer_to_add);
            expansion_front.push_back(customer_to_add); 
        }
    }
    return selected_customers_list;
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    float strategy_selector = getRandomFraction(); 

    const float TIE_BREAK_NOISE_FACTOR = 1e-6; 

    if (strategy_selector < 0.40) { // 40% chance: Prioritize by Time Window Tightness (ascending TW_Width)
        for (int customer_id : customers) {
            float score = instance.TW_Width[customer_id] + getRandomFractionFast() * TIE_BREAK_NOISE_FACTOR;
            scored_customers.emplace_back(score, customer_id);
        }
        std::sort(scored_customers.begin(), scored_customers.end());
    } else if (strategy_selector < 0.70) { // 30% chance: Prioritize by Distance from Depot (descending distance)
        for (int customer_id : customers) {
            float score = -instance.distanceMatrix[0][customer_id] + getRandomFractionFast() * TIE_BREAK_NOISE_FACTOR;
            scored_customers.emplace_back(score, customer_id);
        }
        std::sort(scored_customers.begin(), scored_customers.end());
    } else if (strategy_selector < 0.90) { // 20% chance: Prioritize by Demand (descending demand)
        for (int customer_id : customers) {
            float score = -instance.demand[customer_id] + getRandomFractionFast() * TIE_BREAK_NOISE_FACTOR;
            scored_customers.emplace_back(score, customer_id);
        }
        std::sort(scored_customers.begin(), scored_customers.end());
    } else { // 10% chance: Purely Random Order
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return; 
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}