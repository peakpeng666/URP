#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort and std::swap
#include <utility>   // For std::pair

// Include Utils.h for getRandomNumber, getRandomFractionFast
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> selectedCustomers_list; // To maintain insertion order for expansion

    // Determine the number of customers to remove (stochastic range)
    // For 500+ customers, removing 15-30 customers is a good balance
    // between perturbation strength and speed.
    int min_remove = 15;
    int max_remove = 30;
    int num_to_remove = getRandomNumber(min_remove, max_remove);

    // Counter to detect if local expansion is stuck, prompting a new seed
    int consecutive_failed_expansions = 0;
    const int max_consecutive_failed_expansions = 10; 

    // Pick a random initial seed customer (customer IDs are 1-based)
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers_set.insert(seed_customer);
    selectedCustomers_list.push_back(seed_customer);

    while (selectedCustomers_set.size() < num_to_remove) {
        bool added_customer_in_iteration = false;

        // If local expansion from current selected customers has failed multiple times,
        // pick a completely new random customer as a seed to ensure diversity and meet the target size.
        if (consecutive_failed_expansions >= max_consecutive_failed_expansions) {
            int new_seed = -1;
            int search_attempts = 0;
            // Iterate up to 2*N times to find an unselected customer as a new seed.
            // This is a robust fallback for sparsely connected graphs or small `num_to_remove`
            // values relative to total customers.
            while (search_attempts < sol.instance.numCustomers * 2) {
                int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers_set.find(potential_seed) == selectedCustomers_set.end()) {
                    new_seed = potential_seed;
                    break;
                }
                search_attempts++;
            }

            if (new_seed != -1) {
                selectedCustomers_set.insert(new_seed);
                selectedCustomers_list.push_back(new_seed);
                added_customer_in_iteration = true;
                consecutive_failed_expansions = 0; // Reset counter after successful new seed
            } else {
                // Should theoretically not happen unless almost all customers are selected,
                // or instance has 0 customers, but as a safeguard.
                break;
            }
        }

        // Check if target reached after adding a new seed
        if (selectedCustomers_set.size() >= num_to_remove) break;

        // Try to expand the cluster from an already selected customer.
        // Pick a random customer from the `selectedCustomers_list` to ensure fairness
        // and allow expansion from any part of the growing cluster.
        int current_customer_to_expand_from = selectedCustomers_list[getRandomNumber(0, selectedCustomers_list.size() - 1)];

        // Stochastically decide how many closest neighbors to consider.
        // Limiting this keeps the heuristic fast.
        int neighbors_to_consider = getRandomNumber(3, 7); 
        // Probability to add a suitable neighbor, adds stochasticity to cluster shape.
        float p_add_neighbor = 0.7f; 

        // Iterate through the closest neighbors (adj list is sorted by distance).
        for (int neighbor : sol.instance.adj[current_customer_to_expand_from]) {
            if (selectedCustomers_set.find(neighbor) == selectedCustomers_set.end()) { // If neighbor not already selected
                if (getRandomFractionFast() < p_add_neighbor) { // Stochastic decision to add
                    selectedCustomers_set.insert(neighbor);
                    selectedCustomers_list.push_back(neighbor);
                    added_customer_in_iteration = true;
                    if (selectedCustomers_set.size() >= num_to_remove) break; // Target reached
                }
            }
            neighbors_to_consider--;
            if (neighbors_to_consider <= 0) break; // Stop checking after `neighbors_to_consider`
        }

        if (!added_customer_in_iteration) {
            consecutive_failed_expansions++;
        } else {
            consecutive_failed_expansions = 0; // Reset if new customer was added
        }
    }

    return selectedCustomers_list;
}


// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // A list of pairs: (score, customer_id)
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // Calculate a "closeness score" for each removed customer.
    // The score is the sum of distances from the current customer to all *other removed customers*.
    // A smaller score means the customer is more "central" to the group of removed customers.
    // This aims to reinsert the "core" of the removed cluster first, allowing other
    // removed customers to attach to these core customers during greedy reinsertion.
    for (int customer_id : customers) {
        float score = 0.0f;
        for (int other_customer_id : customers) {
            if (customer_id == other_customer_id) continue;
            score += instance.distanceMatrix[customer_id][other_customer_id];
        }
        customer_scores.push_back({score, customer_id});
    }

    // Sort the customers based on their calculated closeness score in ascending order.
    // Customers most central to the removed set will appear first.
    std::sort(customer_scores.begin(), customer_scores.end());

    // Apply the sorted order back to the 'customers' vector.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }

    // Introduce stochasticity by slightly perturbing the sorted order.
    // Swap adjacent elements with a low probability. This maintains the general
    // ordered structure but introduces diversity in reinsertion sequence over iterations.
    float perturbation_probability = 0.2f; // 20% chance to swap adjacent elements
    for (size_t i = 0; i < customers.size() - 1; ++i) {
        if (getRandomFractionFast() < perturbation_probability) {
            std::swap(customers[i], customers[i+1]);
        }
    }
}