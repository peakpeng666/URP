#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility> 
#include <limits>  

// Assumed external helper functions for random number generation:
// getRandomNumber(int min, int max): Returns a random integer between min and max (inclusive).
// getRandomFraction(): Returns a random float between 0.0 and 1.0 (inclusive).
// getRandomFractionFast(): Returns a faster, possibly less uniform, random float between 0.0 and 1.0.

// Thread-local random number generator for std::shuffle
static thread_local std::mt19937 gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove for this iteration.
    // This value is kept small (10-20) as per LNS best practices for large instances.
    int numCustomersToRemove = getRandomNumber(10, 20);

    // Handle edge cases where no customers exist or no customers should be removed.
    if (sol.instance.numCustomers == 0 || numCustomersToRemove == 0) {
        return {};
    }

    // `selectedCustomersVec` stores the customers in the order they are selected.
    // It is used to pick pivot customers from the growing set.
    std::vector<int> selectedCustomersVec;
    selectedCustomersVec.reserve(numCustomersToRemove); // Pre-allocate memory to improve performance.

    // `selectedCustomersSet` provides fast O(1) average-case lookup to check if a customer
    // has already been selected, preventing duplicates.
    std::unordered_set<int> selectedCustomersSet;

    // Start by selecting a random customer to seed the removal set.
    // Customer IDs are typically 1 to N, with 0 being the depot.
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersVec.push_back(seedCustomer);
    selectedCustomersSet.insert(seedCustomer);

    // Iteratively select remaining customers until the desired count is reached.
    while (static_cast<int>(selectedCustomersVec.size()) < numCustomersToRemove) {
        // Randomly pick an already selected customer to act as a "pivot".
        // This encourages selecting customers that are "close" to the existing removed set,
        // fulfilling the requirement for proximity.
        int pivotIndex = getRandomNumber(0, static_cast<int>(selectedCustomersVec.size()) - 1);
        int pivotCustomer = selectedCustomersVec[pivotIndex];

        int candidateCustomer = -1; // Initialize candidate to an invalid value.

        // Introduce stochastic behavior: 80% chance to select a customer from the pivot's neighbors
        // (physical proximity), 20% chance to select from customers in the same tour (logical proximity).
        if (getRandomFractionFast() < 0.80) { 
            const std::vector<int>& neighbors = sol.instance.adj[pivotCustomer];
            if (!neighbors.empty()) {
                // To keep the operation fast, only consider a small random subset of neighbors.
                int numNeighborsToConsider = std::min(static_cast<int>(neighbors.size()), getRandomNumber(1, 10));
                // Ensure there are valid neighbors within the considered subset.
                if (numNeighborsToConsider > 0) { 
                    candidateCustomer = neighbors[getRandomNumber(0, numNeighborsToConsider - 1)];
                }
            }
        } else { 
            // Attempt to find a candidate from the same tour as the pivot customer.
            int tour_idx = sol.customerToTourMap[pivotCustomer];
            if (tour_idx >= 0 && tour_idx < static_cast<int>(sol.tours.size()) && !sol.tours[tour_idx].customers.empty()) {
                const std::vector<int>& tour_customers = sol.tours[tour_idx].customers;
                
                // Limit attempts to find a new, unselected customer from the tour to maintain speed.
                int max_attempts = 10; 
                for (int attempt = 0; attempt < max_attempts; ++attempt) {
                    int rand_idx = getRandomNumber(0, static_cast<int>(tour_customers.size()) - 1);
                    int potential_candidate = tour_customers[rand_idx];
                    
                    // A valid candidate must not be the depot (customer 0), not the pivot itself,
                    // and not already present in the `selectedCustomersSet`.
                    if (potential_candidate != pivotCustomer && potential_candidate != 0 && 
                        selectedCustomersSet.find(potential_candidate) == selectedCustomersSet.end()) {
                        candidateCustomer = potential_candidate;
                        break; // Valid candidate found, exit search loop.
                    }
                }
            }
        }
        
        // If a valid and unique candidate was identified, add it to both tracking structures.
        if (candidateCustomer != -1 && candidateCustomer != 0 && selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
            selectedCustomersVec.push_back(candidateCustomer);
            selectedCustomersSet.insert(candidateCustomer);
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Stochastically choose a sorting strategy to introduce diversity across iterations.
    // 0: Pure shuffle, 1: Time window tightness, 2: Distance to depot, 3: Demand + service time.
    int sortType = getRandomNumber(0, 3); 

    if (sortType == 0) {
        // A pure random shuffle provides maximum diversity and is fast (O(N)).
        std::shuffle(customers.begin(), customers.end(), gen);
    } else {
        // For other sort types, customers are scored and then sorted.
        std::vector<std::pair<float, int>> scoredCustomers;
        scoredCustomers.reserve(customers.size()); // Pre-allocate memory.

        // Introduce stochastic weights to the scoring criteria, ensuring slight variations
        // in sorting preferences over millions of iterations.
        float w_demand_stoch = getRandomFraction(-0.01f, 0.01f);
        float w_service_stoch = getRandomFraction(-0.01f, 0.01f);

        // Calculate a score for each customer based on the chosen strategy.
        for (int customerId : customers) {
            float score = 0.0f;
            // Add a small random noise to break ties and introduce minor, fast variations.
            float noise = getRandomFractionFast() * 1e-6f; 

            if (sortType == 1) { // Prioritize customers with tighter time windows.
                float tw_width = instance.TW_Width[customerId];
                float tw_tightness = 0.0f;
                if (tw_width > 0.0f) {
                    tw_tightness = 1.0f / tw_width;
                } else {
                    // Assign a very high tightness for zero-width time windows (instantaneous).
                    tw_tightness = std::numeric_limits<float>::max(); 
                }
                score = tw_tightness * 100.0f; // Scale for impact.
                score += instance.startTW[customerId] * 0.001f; // Slight preference for earlier start times.
                score += w_demand_stoch * instance.demand[customerId];
                score += w_service_stoch * instance.serviceTime[customerId];
                score += noise;
            } else if (sortType == 2) { // Prioritize customers closer to the depot.
                score = instance.distanceMatrix[0][customerId]; // Distance from depot (customer 0).
                // Add a small random influence from time window width.
                score += (getRandomFractionFast() * 0.05f) * instance.TW_Width[customerId];
                score += w_demand_stoch * instance.demand[customerId];
                score += w_service_stoch * instance.serviceTime[customerId];
                score += noise;
            } else if (sortType == 3) { // Prioritize customers with higher demand or service time (total load).
                score = instance.demand[customerId] + instance.serviceTime[customerId];
                score += w_demand_stoch * instance.distanceMatrix[0][customerId]; // Influence of distance.
                score += noise;
            }
            scoredCustomers.push_back({score, customerId});
        }

        // Sort the customers based on their calculated scores in descending order.
        // For a small number of customers (10-20), O(N log N) sort is extremely fast.
        std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
            return a.first > b.first; 
        });

        // Apply a final stochastic reordering to the sorted list.
        // This ensures the general ordering is maintained but introduces small, controlled perturbations.
        std::vector<int> finalSortedCustomers;
        finalSortedCustomers.reserve(customers.size());

        int currentProcessedIndex = 0;
        while (currentProcessedIndex < static_cast<int>(scoredCustomers.size())) {
            // Define a small random window (1 to 5 elements) within the remaining sorted customers.
            int maxWindowSize = std::min(static_cast<int>(scoredCustomers.size()) - currentProcessedIndex, getRandomNumber(1, 5));
            
            // Randomly pick one customer from this window.
            int pickOffset = getRandomNumber(0, maxWindowSize - 1);
            int chosenCustomerAbsoluteIndex = currentProcessedIndex + pickOffset;

            // Add the chosen customer to the final reordered list.
            finalSortedCustomers.push_back(scoredCustomers[chosenCustomerAbsoluteIndex].second);

            // Swap the chosen customer to the `currentProcessedIndex` position.
            // This effectively "removes" it from future consideration in the window selections
            // for the current pass, ensuring each customer is picked exactly once.
            std::iter_swap(scoredCustomers.begin() + chosenCustomerAbsoluteIndex, scoredCustomers.begin() + currentProcessedIndex);
            currentProcessedIndex++; // Move to the next position for the next window selection.
        }
        // Update the original 'customers' vector with the new stochastically sorted order.
        customers = finalSortedCustomers;
    }
}