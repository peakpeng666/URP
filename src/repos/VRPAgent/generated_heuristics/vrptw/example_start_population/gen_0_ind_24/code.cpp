#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::min, std::sort
#include <vector>
#include <utility>   // For std::pair
#include <limits>    // For std::numeric_limits
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove == 0) return {};
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    
    selectedCustomers.insert(getRandomNumber(1, sol.instance.numCustomers));

    const int MAX_EXPANSION_ATTEMPTS_PER_ITERATION = 10; 

    while (selectedCustomers.size() < numCustomersToRemove) {
        bool customer_added_in_this_loop = false;

        for (int attempt = 0; attempt < MAX_EXPANSION_ATTEMPTS_PER_ITERATION; ++attempt) {
            std::vector<int> current_selected_vec(selectedCustomers.begin(), selectedCustomers.end());
            int customer_to_expand_from = current_selected_vec[getRandomNumber(0, current_selected_vec.size() - 1)];

            const std::vector<int>& neighbors = sol.instance.adj[customer_to_expand_from];
            int num_neighbors_to_check = std::min((int)neighbors.size(), getRandomNumber(5, 10)); 

            for (int i = 0; i < num_neighbors_to_check; ++i) {
                int potential_new_customer = neighbors[i];
                if (potential_new_customer != 0 && selectedCustomers.find(potential_new_customer) == selectedCustomers.end()) {
                    if (getRandomFraction() < 0.7f) {
                        selectedCustomers.insert(potential_new_customer);
                        customer_added_in_this_loop = true;
                        break; 
                    }
                }
            }
            if (customer_added_in_this_loop) break;
        }

        if (!customer_added_in_this_loop) {
            int new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.find(new_random_customer) != selectedCustomers.end()) {
                new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(new_random_customer);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) return;

    std::vector<float> effective_keys_for_removed_customers;
    effective_keys_for_removed_customers.reserve(customers.size());

    float min_overall_tw_width = std::numeric_limits<float>::max();
    float max_overall_tw_width = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        if (instance.TW_Width[i] < min_overall_tw_width) min_overall_tw_width = instance.TW_Width[i];
        if (instance.TW_Width[i] > max_overall_tw_width) max_overall_tw_width = instance.TW_Width[i];
    }
    float tw_width_range = max_overall_tw_width - min_overall_tw_width;
    float perturbation_magnitude = std::max(0.01f, 0.01f * tw_width_range);

    for (int customer_id : customers) {
        float base_key = instance.TW_Width[customer_id];
        float stochastic_perturbation = getRandomFraction(-perturbation_magnitude, perturbation_magnitude);
        float effective_key = base_key + stochastic_perturbation;
        effective_keys_for_removed_customers.push_back(effective_key);
    }

    std::vector<int> original_indices_sorted = argsort(effective_keys_for_removed_customers);

    std::vector<int> reordered_customers_temp;
    reordered_customers_temp.reserve(customers.size());
    for (int original_idx_in_removed_list : original_indices_sorted) {
        reordered_customers_temp.push_back(customers[original_idx_in_removed_list]);
    }
    customers = reordered_customers_temp;
}