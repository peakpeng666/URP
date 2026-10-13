#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int min_remove = 8;
    const int max_remove = 22;
    int numCustomersToRemove = getRandomNumber(min_remove, max_remove);

    std::vector<int> selectedCustomersVec;
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> potentialSeeds;

    if (numCustomersToRemove <= 0) {
        return {};
    }

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersVec.push_back(initial_seed);
    selectedCustomersSet.insert(initial_seed);
    potentialSeeds.push_back(initial_seed);

    const int max_adj_neighbors_to_check = 30; // Limit the number of neighbors to check for speed

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        if (potentialSeeds.empty()) {
            int new_seed = -1;
            int counter = 0;
            const int max_tries = 1000;
            do {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                counter++;
            } while (selectedCustomersSet.count(new_seed) && counter < max_tries);

            if (selectedCustomersSet.count(new_seed)) {
                 for (int c_id = 1; c_id <= sol.instance.numCustomers; ++c_id) {
                     if (!selectedCustomersSet.count(c_id)) {
                         new_seed = c_id;
                         break;
                     }
                 }
            }
            
            if (new_seed == -1 || selectedCustomersSet.count(new_seed)) {
                // Fallback: if all customers are selected or cannot find a new one, return what we have
                break;
            }

            selectedCustomersVec.push_back(new_seed);
            selectedCustomersSet.insert(new_seed);
            potentialSeeds.push_back(new_seed);
            
            if (selectedCustomersVec.size() == numCustomersToRemove) {
                break;
            }
        }

        int pivot_idx = getRandomNumber(0, static_cast<int>(potentialSeeds.size()) - 1);
        int pivot_customer = potentialSeeds[pivot_idx];

        std::vector<int> unselected_neighbors;
        const auto& adj_list = sol.instance.adj[pivot_customer];
        int neighbors_checked = 0;
        for (int neighbor : adj_list) {
            if (neighbors_checked >= max_adj_neighbors_to_check) {
                break;
            }
            if (!selectedCustomersSet.count(neighbor)) {
                unselected_neighbors.push_back(neighbor);
            }
            neighbors_checked++;
        }

        if (!unselected_neighbors.empty()) {
            int choice_idx = getRandomNumber(0, static_cast<int>(unselected_neighbors.size()) - 1);
            int new_customer_to_add = unselected_neighbors[choice_idx];

            selectedCustomersVec.push_back(new_customer_to_add);
            selectedCustomersSet.insert(new_customer_to_add);
            potentialSeeds.push_back(new_customer_to_add);
        } else {
            std::swap(potentialSeeds[pivot_idx], potentialSeeds.back());
            potentialSeeds.pop_back();
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int num_removed = static_cast<int>(customers.size());
    std::vector<int> sorted_customers;
    std::unordered_set<int> placed_customers;

    int first_idx = getRandomNumber(0, num_removed - 1);
    int current_customer_to_sort = customers[first_idx];
    
    sorted_customers.reserve(num_removed);
    sorted_customers.push_back(current_customer_to_sort);
    placed_customers.insert(current_customer_to_sort);

    const int selection_pool_limit = 5;

    for (int i = 0; i < num_removed - 1; ++i) {
        std::vector<std::pair<float, int>> potential_next_customers;
        potential_next_customers.reserve(num_removed - sorted_customers.size());

        for (int c : customers) {
            if (!placed_customers.count(c)) {
                float dist = instance.distanceMatrix[current_customer_to_sort][c];
                potential_next_customers.push_back({dist, c});
            }
        }

        if (potential_next_customers.empty()) {
            break; 
        }

        std::sort(potential_next_customers.begin(), potential_next_customers.end());

        int pool_size = std::min(selection_pool_limit, static_cast<int>(potential_next_customers.size()));
        int choice_idx = getRandomNumber(0, pool_size - 1);
        int next_customer = potential_next_customers[choice_idx].second;
        
        sorted_customers.push_back(next_customer);
        placed_customers.insert(next_customer);
        current_customer_to_sort = next_customer;
    }

    customers = sorted_customers;
}