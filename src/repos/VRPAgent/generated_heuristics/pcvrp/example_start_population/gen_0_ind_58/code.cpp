#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort and std::shuffle
#include <utility>   // For std::pair

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> removed_set;
    std::vector<int> candidates_for_expansion;

    int num_to_remove = getRandomNumber(10, 20); // Select 10 to 20 customers

    // Seed selection: Start with a random customer
    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    removed_set.insert(initial_customer_id);

    // Add initial_customer_id's nearest neighbors to candidates for expansion
    int num_neighbors_to_consider = std::min((int)sol.instance.adj[initial_customer_id].size(), 5);
    for (int i = 0; i < num_neighbors_to_consider; ++i) {
        candidates_for_expansion.push_back(sol.instance.adj[initial_customer_id][i]);
    }

    // If initial_customer_id is visited, add other customers from its tour to candidates
    if (sol.customerToTourMap[initial_customer_id] != -1) {
        const Tour& tour = sol.tours[sol.customerToTourMap[initial_customer_id]];
        int num_tour_customers_to_consider = std::min((int)tour.customers.size(), 3);
        // Shuffle tour customers to pick random ones, then take the first few
        std::vector<int> tour_customers_shuffled = tour.customers;
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(tour_customers_shuffled.begin(), tour_customers_shuffled.end(), gen);

        for (int i = 0; i < num_tour_customers_to_consider; ++i) {
            if (tour_customers_shuffled[i] != initial_customer_id) { // Don't add the initial_customer_id again
                candidates_for_expansion.push_back(tour_customers_shuffled[i]);
            }
        }
    }

    // Iterative selection: expand the removed set
    while (removed_set.size() < num_to_remove) {
        int next_customer = -1;
        
        // Stochastic choice: primarily expand from existing group, occasionally pick randomly
        // 80% chance to pick from candidates, 20% chance to pick completely random
        if (!candidates_for_expansion.empty() && getRandomFraction() < 0.8) {
            int rand_idx = getRandomNumber(0, candidates_for_expansion.size() - 1);
            next_customer = candidates_for_expansion[rand_idx];
            // Remove the selected candidate to avoid re-selecting it immediately
            candidates_for_expansion.erase(candidates_for_expansion.begin() + rand_idx);
        } else {
            next_customer = getRandomNumber(1, sol.instance.numCustomers);
        }

        // Add customer if not already in the removed set
        if (next_customer != -1 && removed_set.find(next_customer) == removed_set.end()) {
            removed_set.insert(next_customer);

            // Add this newly selected customer's neighbors to `candidates_for_expansion`
            int current_customer_neighbors_to_add = std::min((int)sol.instance.adj[next_customer].size(), 5);
            for (int i = 0; i < current_customer_neighbors_to_add; ++i) {
                candidates_for_expansion.push_back(sol.instance.adj[next_customer][i]);
            }

            // If the customer is part of a tour, add other customers from that tour to `candidates_for_expansion`
            if (sol.customerToTourMap[next_customer] != -1) {
                const Tour& tour = sol.tours[sol.customerToTourMap[next_customer]];
                int current_tour_customers_to_add = std::min((int)tour.customers.size(), 3);
                // Shuffle tour customers to pick random ones, then take the first few
                std::vector<int> current_tour_customers_shuffled = tour.customers;
                static thread_local std::mt19937 gen(std::random_device{}());
                std::shuffle(current_tour_customers_shuffled.begin(), current_tour_customers_shuffled.end(), gen);

                for (int i = 0; i < current_tour_customers_to_add; ++i) {
                    if (current_tour_customers_shuffled[i] != next_customer) { // Don't add the next_customer again
                        candidates_for_expansion.push_back(current_tour_customers_shuffled[i]);
                    }
                }
            }
        }
    }
    return std::vector<int>(removed_set.begin(), removed_set.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Use a hash set for fast lookup of customers within the removed set
    std::unordered_set<int> removed_customers_set(customers.begin(), customers.end());

    // Prepare for sorting based on various metrics
    std::vector<std::pair<int, float>> customer_scores; // Pair of (customer_id, score)

    // Randomly choose a sorting strategy for this iteration
    // 0: Prize descending (higher prize first)
    // 1: Demand ascending (easier to fit small demand first)
    // 2: Proximity to other removed customers descending (reconnect clusters)
    // 3: Distance to depot ascending (closer to depot first)
    // 4: Pure random shuffle
    int strategy_choice = getRandomNumber(0, 4);

    if (strategy_choice == 4) { // Pure random shuffle
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    for (int customer_id : customers) {
        float score = 0.0f;
        switch (strategy_choice) {
            case 0: // Prize descending
                score = instance.prizes[customer_id];
                customer_scores.push_back({customer_id, -score}); // Use negative score to sort descending by prize (ascending by negative score)
                break;
            case 1: // Demand ascending
                score = (float)instance.demand[customer_id];
                customer_scores.push_back({customer_id, score}); // Lower demand means smaller score
                break;
            case 2: // Proximity to other removed customers descending
                {
                    int num_nearby_removed = 0;
                    // Check a limited number of nearest neighbors for speed
                    int num_neighbors_to_check = std::min((int)instance.adj[customer_id].size(), 10);
                    for (int i = 0; i < num_neighbors_to_check; ++i) {
                        int neighbor = instance.adj[customer_id][i];
                        if (removed_customers_set.count(neighbor)) { // Check if neighbor is also in the removed set
                            num_nearby_removed++;
                        }
                    }
                    score = (float)num_nearby_removed;
                    customer_scores.push_back({customer_id, -score}); // Higher count means smaller negative score
                }
                break;
            case 3: // Distance to depot ascending
                score = instance.distanceMatrix[0][customer_id];
                customer_scores.push_back({customer_id, score}); // Shorter distance means smaller score
                break;
            default:
                // Fallback to random if an invalid strategy is chosen, should not happen.
                static thread_local std::mt19937 gen(std::random_device{}());
                std::shuffle(customers.begin(), customers.end(), gen);
                return;
        }
    }

    // Sort the customer_scores vector based on the calculated scores
    std::sort(customer_scores.begin(), customer_scores.end(),
              [](const std::pair<int, float>& a, const std::pair<int, float>& b) {
                  return a.second < b.second; // Sort by score ascending
              });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].first;
    }
}