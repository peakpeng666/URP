#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::min, std::swap
#include <vector>
#include <utility>   // For std::pair
#include "Utils.h"   // Assumed to provide getRandomNumber, getRandomFractionFast

// Define constants for heuristic parameters
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;
const int NUM_NEIGHBORS_TO_EXPLORE = 5; // For select_by_llm_1, number of nearest neighbors to add to pool

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesPool;
    std::unordered_set<int> candidatesPoolSet; // For quick lookup in candidatesPool

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    // Loop until enough customers are selected
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int chosen_c;

        if (candidatesPool.empty()) {
            // No more candidates in the current "cluster". Start a new one.
            do {
                chosen_c = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.count(chosen_c)); // Ensure the new seed is not already selected
        } else {
            // Select a customer from the candidates pool using a random choice
            int rand_idx = getRandomNumber(0, static_cast<int>(candidatesPool.size()) - 1);
            chosen_c = candidatesPool[rand_idx];

            // Efficiently remove chosen_c from candidatesPool and candidatesPoolSet
            std::swap(candidatesPool[rand_idx], candidatesPool.back());
            candidatesPool.pop_back();
            candidatesPoolSet.erase(chosen_c);

            // If by some chance (due to a race condition or prior state) it's already selected, skip
            if (selectedCustomersSet.count(chosen_c)) {
                continue;
            }
        }

        // Add the chosen customer to the selected set
        selectedCustomersSet.insert(chosen_c);

        // Add its nearest neighbors to the candidates pool for future selection
        // Ensure neighbors are not already selected or already in the candidates pool
        int neighbors_to_check = std::min(static_cast<int>(sol.instance.adj[chosen_c].size()), NUM_NEIGHBORS_TO_EXPLORE);
        for (int i = 0; i < neighbors_to_check; ++i) {
            int neighbor_id = sol.instance.adj[chosen_c][i];
            if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end() &&
                candidatesPoolSet.find(neighbor_id) == candidatesPoolSet.end()) {
                candidatesPool.push_back(neighbor_id);
                candidatesPoolSet.insert(neighbor_id);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Calculate a score for each customer, combining demand and distance from depot
    // Higher score indicates a "harder" customer to place (high demand or far from depot)
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float demand_val = static_cast<float>(instance.demand[customer_id]);
        float dist_val = instance.distanceMatrix[0][customer_id]; // Distance from depot (node 0)

        // Assign weights to demand and distance to prioritize what makes a customer "harder"
        // Adjust weights based on problem scale and desired behavior.
        // E.g., demand is often more restrictive than distance for reinsertion.
        float score = demand_val * 2.0f + dist_val; // Demand weighted more heavily

        customer_scores.push_back({score, customer_id});
    }

    // Use a "roulette wheel" selection method to stochastically sort customers
    // This introduces diversity in ordering while still biasing towards higher scores.
    std::vector<int> sorted_customers;
    sorted_customers.reserve(customers.size());

    std::vector<std::pair<float, int>> current_candidates = customer_scores;

    while (!current_candidates.empty()) {
        std::vector<float> weights;
        weights.reserve(current_candidates.size());
        float current_total_weight = 0.0f;

        for (const auto& p : current_candidates) {
            // Higher scores correspond to higher weights, meaning higher probability of selection
            float weight = p.first;
            // Ensure positive weights for selection
            if (weight < 0.0f) weight = 0.0f; 
            weights.push_back(weight);
            current_total_weight += weight;
        }

        if (current_total_weight == 0.0f) {
            // All remaining candidates have zero or negative weight,
            // fall back to random selection for the rest to avoid infinite loops.
            int rand_idx = getRandomNumber(0, static_cast<int>(current_candidates.size()) - 1);
            sorted_customers.push_back(current_candidates[rand_idx].second);
            std::swap(current_candidates[rand_idx], current_candidates.back());
            current_candidates.pop_back();
            continue;
        }

        float rand_val = getRandomFractionFast() * current_total_weight;
        int chosen_idx = -1;
        float cumulative_weight = 0.0f;

        for (size_t i = 0; i < weights.size(); ++i) {
            cumulative_weight += weights[i];
            if (rand_val <= cumulative_weight) {
                chosen_idx = static_cast<int>(i);
                break;
            }
        }
        
        // Fallback in case floating point precision issues prevent finding an index
        if (chosen_idx == -1) {
            chosen_idx = getRandomNumber(0, static_cast<int>(current_candidates.size()) - 1);
        }

        sorted_customers.push_back(current_candidates[chosen_idx].second);
        std::swap(current_candidates[chosen_idx], current_candidates.back());
        current_candidates.pop_back();
    }

    customers = sorted_customers;
}