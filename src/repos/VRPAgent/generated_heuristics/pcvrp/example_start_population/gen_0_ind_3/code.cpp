#include "AgentDesigned.h" // Assuming this includes Solution.h, Instance.h, Tour.h
#include <random>           // For std::random_device, std::mt19937
#include <unordered_set>    // For std::unordered_set
#include <algorithm>        // For std::sort, std::shuffle, std::max
#include <vector>           // For std::vector
#include <utility>          // For std::pair
#include "Utils.h"          // For getRandomNumber, getRandomFractionFast etc.


// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove. Keep it small for large instances.
    int numCustomersToRemove = getRandomNumber(10, 30); // Random count between 10 and 30

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList; // To maintain order of selection, if needed, or for final return

    // Handle edge cases for numCustomersToRemove
    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        numCustomersToRemove = 1; // Always remove at least one customer if possible
    }

    // Use thread_local for random number generator for performance in a multi-threaded context
    static thread_local std::mt19937 gen(std::random_device{}());

    // Step 1: Select a random seed customer
    // Customers are 1-indexed in the problem description (e.g., customerToTourMap).
    // instance.numCustomers refers to total customers excluding depot.
    int seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seed_customer_id);
    selectedCustomersList.push_back(seed_customer_id);

    // Step 2: Iteratively expand by selecting neighbors of already selected customers
    // to ensure proximity and introduce stochasticity.
    std::vector<int> candidatePool; // Stores potential customers to select next

    // Add closest neighbors of the seed to the candidate pool
    // sol.instance.adj stores neighbors sorted by distance.
    for (int neighbor_id : sol.instance.adj[seed_customer_id]) {
        if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers) { // Ensure it's a valid customer ID
            if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                candidatePool.push_back(neighbor_id);
            }
        }
    }
    // Initial shuffle of the candidate pool for stochasticity
    std::shuffle(candidatePool.begin(), candidatePool.end(), gen);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int customer_to_add = -1;

        // Try to pick from candidate pool first
        while (!candidatePool.empty()) {
            int idx = getRandomNumber(0, static_cast<int>(candidatePool.size()) - 1);
            int potential_customer = candidatePool[idx];
            
            // Remove from candidate pool regardless, as we've processed it for this iteration
            candidatePool.erase(candidatePool.begin() + idx);

            if (selectedCustomersSet.find(potential_customer) == selectedCustomersSet.end()) {
                customer_to_add = potential_customer;
                break; // Found a valid customer to add
            }
        }

        // If candidate pool is exhausted or all candidates were already selected
        if (customer_to_add == -1) {
            // Fallback: Pick a completely random unselected customer
            // This ensures we always reach `numCustomersToRemove`.
            int attempts = 0;
            while (attempts < 1000) { // Limit attempts to prevent infinite loop on very small instances
                int random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(random_unselected_customer) == selectedCustomersSet.end()) {
                    customer_to_add = random_unselected_customer;
                    break;
                }
                attempts++;
            }
            if (customer_to_add == -1) { // If still no customer found after attempts (e.g. all are selected)
                break; // Cannot find enough customers, exit early
            }
        }
        
        selectedCustomersSet.insert(customer_to_add);
        selectedCustomersList.push_back(customer_to_add);

        // Add neighbors of the newly added customer to the candidate pool for future selections
        // This promotes the "each selected customer should be close to at least one or a few other selected customers" rule.
        for (int neighbor_id : sol.instance.adj[customer_to_add]) {
            if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers) { // Ensure valid customer ID
                if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                    // Check if already in candidatePool to avoid duplicates and redundant processing
                    bool found_in_candidates = false;
                    for (int c : candidatePool) { // Linear search is acceptable for small candidatePool size
                        if (c == neighbor_id) {
                            found_in_candidates = true;
                            break;
                        }
                    }
                    if (!found_in_candidates) {
                        candidatePool.push_back(neighbor_id);
                    }
                }
            }
        }
        // Reshuffle candidate pool after adding new neighbors for the next iteration's random selection
        std::shuffle(candidatePool.begin(), candidatePool.end(), gen);
    }

    return selectedCustomersList;
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Use thread_local for random number generator for performance in a multi-threaded context
    static thread_local std::mt19937 gen(std::random_device{}());

    // Calculate a dynamic noise scale based on the prizes in the current batch of customers.
    float max_prize_in_batch = 0.0f;
    for (int customer_id : customers) {
        if (instance.prizes[customer_id] > max_prize_in_batch) {
            max_prize_in_batch = instance.prizes[customer_id];
        }
    }
    // Set a minimum noise scale to ensure diversity even if prizes are all zero or very small.
    // The noise will be up to 15% of the maximum prize in the current batch of customers.
    const float MIN_NOISE_SCALE = 1.0f; 
    float current_noise_scale = std::max(MIN_NOISE_SCALE, max_prize_in_batch * 0.15f);

    for (int customer_id : customers) {
        // Calculate a base score: prioritize high prize, penalize high demand
        // The weight 0.2f for demand is an arbitrary heuristic; it can be tuned.
        float score = instance.prizes[customer_id] - static_cast<float>(instance.demand[customer_id]) * 0.2f;
        
        // Add significant stochastic noise to the score to ensure diversity over many iterations.
        // getRandomFractionFast() returns a float in [0.0, 1.0].
        // (getRandomFractionFast() - 0.5f) results in a float in [-0.5, 0.5].
        // Multiplying by current_noise_scale gives noise in [-0.5 * current_noise_scale, 0.5 * current_noise_scale].
        score += (getRandomFractionFast() - 0.5f) * current_noise_scale;
        
        scored_customers.push_back({score, customer_id});
    }

    // Sort customers based on their calculated scores in descending order.
    // Customers with higher scores (more profitable/easier to reinsert) will be reinserted earlier.
    std::sort(scored_customers.begin(), scored_customers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; 
              });

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}