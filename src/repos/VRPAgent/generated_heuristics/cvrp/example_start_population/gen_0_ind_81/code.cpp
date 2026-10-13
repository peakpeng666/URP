#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle
#include <vector>
#include <utility>   // For std::pair

// Ensure Utils.h functions are available
#include "Utils.h" 

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> activeGrowthPoints; // Customers from which we will try to grow the removal set

    int numCustomersToRemove = getRandomNumber(10, 20); // Number of customers to remove
    const Instance& instance = sol.instance;

    // Determine the number of initial seeds to start growing from (1 or 2 centers)
    int numInitialSeeds = getRandomNumber(1, 2); 
    
    // Select initial seed customers
    for (int i = 0; i < numInitialSeeds; ++i) {
        int seed_customer = getRandomNumber(1, instance.numCustomers);
        // Ensure the seed is unique among selected customers
        while (selectedCustomers.count(seed_customer) > 0) {
            seed_customer = getRandomNumber(1, instance.numCustomers);
        }
        selectedCustomers.insert(seed_customer);
        activeGrowthPoints.push_back(seed_customer);
    }

    // Grow the set of selected customers by adding neighbors
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (activeGrowthPoints.empty()) {
            // This happens if all current active growth points have exhausted their close unselected neighbors.
            // Pick a new random unselected customer to act as a new seed for a potentially disconnected removal zone.
            int new_seed = -1;
            // Try a few times to find a random unselected customer
            for (int attempts = 0; attempts < 10; ++attempts) {
                int candidate_seed = getRandomNumber(1, instance.numCustomers);
                if (selectedCustomers.count(candidate_seed) == 0) {
                    new_seed = candidate_seed;
                    break;
                }
            }
            if (new_seed == -1) { 
                // Fallback: iterate through all customers if random attempts fail (very rare for small numCustomersToRemove)
                for (int i = 1; i <= instance.numCustomers; ++i) {
                    if (selectedCustomers.count(i) == 0) {
                        new_seed = i;
                        break;
                    }
                }
                if (new_seed == -1) { // No unselected customers left (should not happen if numCustomersToRemove is small)
                    break; // Cannot add more customers
                }
            }
            selectedCustomers.insert(new_seed);
            activeGrowthPoints.push_back(new_seed);
            continue; // Continue to next iteration of main loop
        }

        // Randomly pick an active customer from which to expand
        int anchor_idx = getRandomNumber(0, (int)activeGrowthPoints.size() - 1);
        int anchor_customer = activeGrowthPoints[anchor_idx];

        bool customer_added_in_round = false;
        // Randomize the number of neighbors to check for more diversity
        int num_neighbors_to_check = getRandomNumber(5, 15); 

        // Iterate through the closest neighbors of the anchor customer
        for (int k = 0; k < std::min(num_neighbors_to_check, (int)instance.adj[anchor_customer].size()); ++k) {
            int neighbor_customer = instance.adj[anchor_customer][k];

            if (selectedCustomers.count(neighbor_customer) == 0) { // If neighbor is not already selected
                selectedCustomers.insert(neighbor_customer);
                activeGrowthPoints.push_back(neighbor_customer); // Add new customer as a potential future growth point
                customer_added_in_round = true;
                break; // Add one neighbor per round to spread the growth
            }
        }

        if (!customer_added_in_round) {
            // If no new neighbor was added from this anchor customer, it means
            // all its closest neighbors are already selected or exhausted.
            // Remove it from active growth points to avoid repeatedly checking it.
            // Efficient removal by swapping with last and popping.
            activeGrowthPoints[anchor_idx] = activeGrowthPoints.back();
            activeGrowthPoints.pop_back();
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Create a vector of pairs to store (score, customer_id)
    std::vector<std::pair<float, int>> scored_customers;

    // Stochastic weighting for demand influence
    // Higher weight means demand has a larger impact on sorting priority
    float weight_demand = getRandomFraction(0.1f, 0.5f); 
    
    // Stochastic noise factor for permutation
    // Adds randomness to break ties and provide diversity
    float noise_factor = getRandomFraction(0.01f, 0.1f); 

    for (int customer_id : customers) {
        // Score based on distance from depot (0-th node)
        float score = instance.distanceMatrix[0][customer_id]; 
        
        // Add demand contribution, weighted stochastically
        score += instance.demand[customer_id] * weight_demand;
        
        // Add a small stochastic perturbation, scaled by distance from depot
        // This helps in breaking ties and introduces diversity across iterations
        score += getRandomFractionFast() * noise_factor * instance.distanceMatrix[0][customer_id]; 

        scored_customers.push_back({score, customer_id});
    }

    // Sort customers by their calculated score in descending order.
    // This prioritizes customers that are "harder" to place first 
    // (e.g., farther from depot, higher demand), allowing more flexibility
    // for subsequent reinsertions.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}