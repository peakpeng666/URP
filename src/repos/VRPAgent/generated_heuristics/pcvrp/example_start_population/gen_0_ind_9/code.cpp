#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include <cmath>     // For std::min, std::fmax
#include "Utils.h"   // For getRandomNumber, getRandomFraction

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec; // To maintain insertion order for potential LNS flow benefits

    // Determine the number of customers to remove
    int numCustomersToRemove = getRandomNumber(10, 20); // A small number, as required

    // Prepare a list of unvisited customers
    std::vector<int> unvisitedCustomers;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] == -1) {
            unvisitedCustomers.push_back(i);
        }
    }
    // Shuffle unvisited customers to ensure randomness if sampled
    std::shuffle(unvisitedCustomers.begin(), unvisitedCustomers.end(), std::mt19937(std::random_device{}()));

    // Pool of candidates for expansion (neighbors of selected customers, and a few initially sampled unvisited customers)
    std::vector<int> candidatePoolVec;
    std::unordered_set<int> candidatePoolSet; // For fast lookup if a customer is already in candidatePoolVec

    // Step 1: Initial seed selection
    // Try to pick a random visited customer first, as removing a customer from an existing tour can lead to more impactful changes.
    // Fallback to any random customer if no visited customer is found after several attempts.
    int initial_seed = -1;
    int attempts = 0;
    while (attempts < 100 && initial_seed == -1) {
        int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
        if (sol.customerToTourMap[rand_cust] != -1) {
            initial_seed = rand_cust;
        }
        attempts++;
    }
    if (initial_seed == -1) { // If no visited customer found, or all customers are unvisited
        initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    }

    selectedCustomersSet.insert(initial_seed);
    selectedCustomersVec.push_back(initial_seed);

    // Add neighbors of the initial seed to the candidate pool
    for (int neighbor : sol.instance.adj[initial_seed]) {
        // Ensure neighbor is a customer (index > 0) and not already selected
        if (neighbor > 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            if (candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
                candidatePoolVec.push_back(neighbor);
                candidatePoolSet.insert(neighbor);
            }
        }
    }

    // Add a subset of unvisited customers to the candidate pool directly.
    // This ensures unvisited customers are considered for reinsertion alongside visited ones,
    // and their neighbors can then be pulled into the selection.
    int numUnvisitedToAdd = std::min((int)unvisitedCustomers.size(), (int)(numCustomersToRemove / 2));
    for (int i = 0; i < numUnvisitedToAdd; ++i) {
        int unvisited_cust = unvisitedCustomers[i];
        if (selectedCustomersSet.find(unvisited_cust) == selectedCustomersSet.end()) {
            if (candidatePoolSet.find(unvisited_cust) == candidatePoolSet.end()) {
                candidatePoolVec.push_back(unvisited_cust);
                candidatePoolSet.insert(unvisited_cust);
            }
        }
    }

    // Step 2: Iteratively expand the set of selected customers
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int next_customer_to_add = -1;

        // Prioritize selecting from the candidate pool (neighbors of already selected or initially added unvisited)
        if (!candidatePoolVec.empty()) {
            int rand_idx = getRandomNumber(0, candidatePoolVec.size() - 1);
            next_customer_to_add = candidatePoolVec[rand_idx];
            
            // Remove chosen customer from the candidate pool (swap with last and pop_back for efficiency)
            candidatePoolVec[rand_idx] = candidatePoolVec.back();
            candidatePoolVec.pop_back();
            candidatePoolSet.erase(next_customer_to_add);
        } else {
            // Fallback: If the candidate pool is empty (e.g., all neighbors of selected customers are already selected)
            // or if the initial seed had very few unselected neighbors, pick any random unselected customer.
            int attempts_fallback = 0;
            while (attempts_fallback < 1000) { // Limit attempts to find an unselected customer
                int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(rand_cust) == selectedCustomersSet.end()) {
                    next_customer_to_add = rand_cust;
                    break;
                }
                attempts_fallback++;
            }
            if (next_customer_to_add == -1) { // If no unselected customer can be found after attempts, break
                 break;
            }
        }
        
        // If the chosen customer is already selected (should not happen if candidatePool management is correct,
        // but included for robustness), skip to the next iteration.
        if (selectedCustomersSet.find(next_customer_to_add) != selectedCustomersSet.end()) {
            continue;
        }

        selectedCustomersSet.insert(next_customer_to_add);
        selectedCustomersVec.push_back(next_customer_to_add);

        // Add neighbors of the newly selected customer to the candidate pool
        for (int neighbor : sol.instance.adj[next_customer_to_add]) {
            // Ensure neighbor is a customer (index > 0) and not already selected or already in the candidate pool
            if (neighbor > 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
                    candidatePoolVec.push_back(neighbor);
                    candidatePoolSet.insert(neighbor);
                }
            }
        }
    }

    return selectedCustomersVec;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers based on a "profitability" score, prioritizing customers that are
    // highly profitable (high prize) relative to their minimum travel cost (to/from depot).
    // This aligns with the PCVRP objective and the greedy reinsertion mechanism's
    // ability to create new tours for single customers.
    // Stochastic noise is added to ensure diversity in sorting order over many iterations.

    std::vector<std::pair<float, int>> customerScores; // Stores (score, customer_idx)
    float min_dist_to_depot = 1.0f; // A small constant to avoid division by zero or very small values if depot is at (0,0) and a customer is also at (0,0) or very close.

    for (int customer_idx : customers) {
        float prize = instance.prizes[customer_idx];
        float dist_to_depot = instance.distanceMatrix[0][customer_idx]; // Distance from depot (node 0) to customer
        
        // Calculate a score: (Prize - (2 * distance_to_depot))
        // This represents the net profit if the customer forms its own tour starting and ending at the depot.
        // Using fmax to ensure a positive or minimal denominator if we were to divide by it.
        float score = prize - (2.0f * dist_to_depot); 
        
        // Add stochastic noise. getRandomFraction() returns a float in [0.0, 1.0].
        // Noise is scaled relative to the customer's prize, ensuring it's significant but doesn't
        // completely randomize the order of vastly different prize values.
        // (getRandomFraction() - 0.5f) makes the noise centered around zero.
        score += (getRandomFraction() - 0.5f) * 0.1f * prize; 

        customerScores.push_back({score, customer_idx});
    }

    // Sort customers in descending order of their calculated score (most profitable first)
    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original `customers` vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}