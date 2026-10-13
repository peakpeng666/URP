#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::min, std::max
#include <vector>    // For std::vector
#include <utility>   // For std::pair

#include "Utils.h" // For getRandomNumber, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_list;

    int min_removals = std::max(10, static_cast<int>(0.02 * sol.instance.numCustomers));
    int max_removals = std::min(30, static_cast<int>(0.06 * sol.instance.numCustomers));
    
    // Ensure min_removals is not greater than max_removals for very small instances
    if (min_removals > max_removals) {
        max_removals = min_removals; 
    }

    int num_to_remove = getRandomNumber(min_removals, max_removals);

    // Cap num_to_remove by the actual number of customers
    num_to_remove = std::min(num_to_remove, sol.instance.numCustomers);
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) {
        num_to_remove = 1; // Always remove at least 1 if customers exist
    }

    if (num_to_remove == 0) { // No customers to remove
        return {};
    }

    // Pick a random initial customer
    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_customer);
    selected_customers_list.push_back(initial_customer);

    int attempts_to_find_neighbor = 0;
    const int max_attempts_per_selection = 20; 

    // Iteratively add neighbors of already selected customers
    while (selected_customers_set.size() < num_to_remove) {
        if (selected_customers_list.empty()) {
            break; 
        }

        int source_idx = getRandomNumber(0, selected_customers_list.size() - 1);
        int current_customer_id = selected_customers_list[source_idx];

        const std::vector<int>& neighbors = sol.instance.adj[current_customer_id];

        bool new_customer_found = false;
        attempts_to_find_neighbor = 0;
        
        while (!new_customer_found && attempts_to_find_neighbor < max_attempts_per_selection) {
            if (neighbors.empty()) {
                break; 
            }

            int num_neighbors_to_consider = std::min(10, (int)neighbors.size());
            if (num_neighbors_to_consider == 0) {
                break;
            }
            int neighbor_choice_idx = getRandomNumber(0, num_neighbors_to_consider - 1);
            int candidate_customer = neighbors[neighbor_choice_idx];

            if (candidate_customer != 0 && selected_customers_set.find(candidate_customer) == selected_customers_set.end()) {
                selected_customers_set.insert(candidate_customer);
                selected_customers_list.push_back(candidate_customer);
                new_customer_found = true;
            }
            attempts_to_find_neighbor++;
        }

        // Fallback: If finding a suitable neighbor fails after several attempts,
        // pick a completely random unselected customer to ensure progress.
        if (!new_customer_found) {
            int random_unselected_customer = -1;
            int fallback_attempts = 0;
            const int max_fallback_attempts = sol.instance.numCustomers * 2; 

            while (fallback_attempts < max_fallback_attempts) {
                int potential_random = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(potential_random) == selected_customers_set.end()) {
                    random_unselected_customer = potential_random;
                    break;
                }
                fallback_attempts++;
            }

            if (random_unselected_customer != -1) {
                selected_customers_set.insert(random_unselected_customer);
                selected_customers_list.push_back(random_unselected_customer);
            } else {
                break; // Cannot find any more unselected customers
            }
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    float max_tw_width = 0.0;
    float max_demand = 0.0;
    float max_service_time = 0.0;

    for (int customer_id : customers) {
        if (instance.TW_Width[customer_id] > max_tw_width) max_tw_width = instance.TW_Width[customer_id];
        if (static_cast<float>(instance.demand[customer_id]) > max_demand) max_demand = static_cast<float>(instance.demand[customer_id]);
        if (instance.serviceTime[customer_id] > max_service_time) max_service_time = instance.serviceTime[customer_id];
    }
    
    // Avoid division by zero
    if (max_tw_width == 0) max_tw_width = 1.0;
    if (max_demand == 0) max_demand = 1.0;
    if (max_service_time == 0) max_service_time = 1.0;

    float tw_weight = 1.0; 
    float demand_weight = 0.5; 
    float service_time_weight = 0.3; 
    float perturbation_strength = 0.1; 

    for (int customer_id : customers) {
        float score = 0.0;

        score += tw_weight * (1.0 - (instance.TW_Width[customer_id] / max_tw_width));
        score += demand_weight * (instance.demand[customer_id] / max_demand);
        score += service_time_weight * (instance.serviceTime[customer_id] / max_service_time);

        score += (getRandomFractionFast() - 0.5) * perturbation_strength;

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; 
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}