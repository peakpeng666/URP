#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFraction, getRandomFractionFast

// Customer selection heuristic
// Selects a subset of customers for removal. The selection strategy
// aims for a balance of locality and diversity, ensuring that most
// removed customers are near at least one other removed customer,
// while incorporating stochastic jumps to prevent getting stuck
// in a single very small region.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec; // To allow random access to already selected customers and maintain order for return

    // Determine the number of customers to remove. A small range is chosen
    // as per LNS best practices for large instances.
    const int minCustomersToRemove = 10;
    const int maxCustomersToRemove = 20; 
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToRemove == 0) {
        return {};
    }

    // 1. Pick an initial random customer as the seed for removal.
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    // Continue adding customers until the desired number is reached.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // Introduce a chance to pick a completely random unselected customer (e.g., 15% of the time).
        // This ensures diversity across LNS iterations and prevents the search from focusing too much
        // on a very localized region, helping to escape local optima.
        if (getRandomFraction() < 0.15) { // Probability of a random jump
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            // Ensure the randomly picked customer is not already selected.
            // Loop a few times to find an unselected one, otherwise fallback to sequential scan.
            int attempts = 0;
            const int maxAttempts = 100;
            while (selectedCustomersSet.count(randomCustomer) && attempts < maxAttempts) {
                randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (!selectedCustomersSet.count(randomCustomer)) { // If an unselected random customer was found
                selectedCustomersSet.insert(randomCustomer);
                selectedCustomersVec.push_back(randomCustomer);
                continue; // Move to the next iteration of the main loop
            }
            // If after maxAttempts, we still couldn't find an unselected random customer,
            // fall through to the neighbor selection logic or the final sequential fallback.
        }

        // 2. Otherwise (most of the time), expand from an already selected customer.
        // Randomly pick a customer from the set of already selected customers.
        int sourceCustomerIdx = selectedCustomersVec[getRandomNumber(0, selectedCustomersVec.size() - 1)];

        bool addedNeighbor = false;
        // Iterate through its neighbors using the precomputed adjacency list, which is sorted by distance.
        // This ensures that the newly selected customer is geographically close to an existing one.
        for (int neighborIdx : sol.instance.adj[sourceCustomerIdx]) {
            // Ensure neighborIdx is a valid customer (not depot, check bounds) and not already selected.
            if (neighborIdx > 0 && neighborIdx <= sol.instance.numCustomers && !selectedCustomersSet.count(neighborIdx)) {
                selectedCustomersSet.insert(neighborIdx);
                selectedCustomersVec.push_back(neighborIdx);
                addedNeighbor = true;
                break; // Found and added the closest unselected neighbor, move to next customer removal
            }
        }

        // Fallback: If no unselected neighbor was found for the chosen source customer
        // (e.g., all its closest neighbors are already selected, or it's an isolated customer).
        // This can happen if the selected cluster is dense, or if numCustomersToRemove is close to total.
        if (!addedNeighbor) {
            // As a robust fallback, try to pick a completely random unselected customer.
            // This is similar to the random jump, but ensures progress if neighbor expansion stalls.
            int randomCustomer = -1;
            int attempts = 0;
            const int maxAttempts = 100; // Limit attempts to ensure speed for large instances
            while (attempts < maxAttempts) {
                int c = getRandomNumber(1, sol.instance.numCustomers);
                if (!selectedCustomersSet.count(c)) {
                    randomCustomer = c;
                    break;
                }
                attempts++;
            }
            
            if (randomCustomer != -1) { // If an unselected random customer was found within attempts
                selectedCustomersSet.insert(randomCustomer);
                selectedCustomersVec.push_back(randomCustomer);
            } else {
                // Ultimate fallback: If even repeated random attempts fail (highly unlikely for small removal sets),
                // iterate through customer IDs sequentially to find the next unselected one.
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (!selectedCustomersSet.count(i)) {
                        selectedCustomersSet.insert(i);
                        selectedCustomersVec.push_back(i);
                        break;
                    }
                }
            }
        }
    }

    return selectedCustomersVec;
}

// Ordering heuristic for removed customers
// This function sorts the removed customers for greedy reinsertion.
// Prioritizes customers that are typically harder to place, such as those with
// tight time windows. Stochasticity is introduced to diversify the reinsertion order.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Use a temporary vector of pairs to store (sorting_key, customer_id).
    // This allows sorting based on the key while preserving the original customer IDs.
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // A factor to control the influence of random noise.
    // This value needs to be tuned based on the typical scale of TW_Width values
    // in the problem instances. A value of 10.0f means random noise up to 10 units.
    const float RANDOM_NOISE_FACTOR = 10.0f; 

    for (int customer_id : customers) {
        // The primary sorting criterion is the Time Window Width (TW_Width).
        // Customers with smaller (tighter) time windows are generally harder to reinsert
        // and should be prioritized.
        float primary_key = instance.TW_Width[customer_id];

        // Add a small stochastic component to the sorting key.
        // This introduces randomness in the order of customers with similar TW_Width,
        // promoting diversity in the LNS search without entirely discarding the heuristic.
        float stochastic_component = getRandomFractionFast() * RANDOM_NOISE_FACTOR;

        float score = primary_key + stochastic_component;
        customer_scores.push_back({score, customer_id});
    }

    // Sort the customers based on their calculated score in ascending order.
    // This places customers with tighter time windows (and lower scores) first.
    std::sort(customer_scores.begin(), customer_scores.end());

    // Update the original 'customers' vector with the new, sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}