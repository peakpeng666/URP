#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::max, std::min
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include <iterator>  // For std::next

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    const Instance& instance = sol.instance;

    // Determine the number of customers to remove
    // This range provides a balance between fixed small numbers and scaling with instance size.
    // For 500 customers, this might be around 10-40 customers (2%-8%).
    int minCustomersToRemove = std::max(5, static_cast<int>(0.02 * instance.numCustomers));
    int maxCustomersToRemove = std::min(50, static_cast<int>(0.08 * instance.numCustomers));
    
    // Ensure min is not greater than max, and set a default small range for very tiny instances.
    if (minCustomersToRemove > maxCustomersToRemove) {
        minCustomersToRemove = 1; // At least one customer
        maxCustomersToRemove = 5; // A very small upper bound for tiny instances
    }
    // Ensure actual range is valid and includes at least one customer
    numCustomersToRemove = std::max(minCustomersToRemove, numCustomersToRemove);
    numCustomersToRemove = std::min(maxCustomersToRemove, numCustomersToRemove);

    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (instance.numCustomers == 0) {
        return {};
    }

    // Step 1: Pick an initial seed customer randomly
    int seedCustomer = getRandomNumber(1, instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);

    // Stochasticity parameter: probability to select a completely random customer
    // A higher value leads to more dispersed removals, a lower value leads to more clustered removals.
    float randomSelectionProbability = 0.25f; // Tunable parameter

    // Step 2: Iteratively add customers until the desired number is reached
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (getRandomFractionFast() < randomSelectionProbability) {
            // Option A: Select a completely random customer from the entire customer set
            int newCustomer = getRandomNumber(1, instance.numCustomers);
            if (selectedCustomersSet.find(newCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(newCustomer);
            }
        } else {
            // Option B: Expand from an already selected customer's neighbors (cluster growth)
            if (selectedCustomersSet.empty()) { 
                // This case should ideally not be reached if a seed is always inserted,
                // but included as a safeguard.
                continue; 
            }
            // Randomly pick an "anchor" customer from the set of already selected customers
            int anchorCustomerIdx = getRandomNumber(0, static_cast<int>(selectedCustomersSet.size()) - 1);
            int anchorCustomer = *std::next(selectedCustomersSet.begin(), anchorCustomerIdx);

            // Find the first unselected neighbor of the anchor customer using the pre-sorted adjacency list
            bool neighborFound = false;
            for (int neighborNode : instance.adj[anchorCustomer]) {
                if (neighborNode == 0) continue; // Skip depot node (node 0)
                // Ensure the neighbor node is a valid customer ID
                if (neighborNode >= 1 && neighborNode <= instance.numCustomers) {
                    if (selectedCustomersSet.find(neighborNode) == selectedCustomersSet.end()) {
                        selectedCustomersSet.insert(neighborNode);
                        neighborFound = true;
                        break;
                    }
                }
            }

            // Fallback: If no unselected neighbor was found for the chosen anchor (e.g., all its neighbors are already selected),
            // or if a rare edge case prevents expansion, pick a random unselected customer as a fallback.
            if (!neighborFound) {
                int newCustomer = getRandomNumber(1, instance.numCustomers);
                if (selectedCustomersSet.find(newCustomer) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(newCustomer);
                }
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

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    // Calculate a "priority score" for each customer to determine reinsertion order.
    // The goal is to prioritize customers that might be "harder" or more "critical" to reinsert first.
    // This often involves high demand customers or those located in key areas.
    for (int customerId : customers) {
        // Factors influencing score:
        // 1. Demand: Customers with higher demand are generally more difficult to fit into existing vehicle capacities.
        // 2. Distance to depot: Customers far from the depot might require longer routes or more capacity commitment.
        // 3. Random perturbation: A small random noise added to the score ensures stochasticity for customers
        //    with very similar primary scores, promoting diversity across LNS iterations.

        float demand_contribution = static_cast<float>(instance.demand[customerId]);
        float distance_contribution = instance.distanceMatrix[0][customerId]; // Distance from depot (node 0)

        // Weights can be tuned based on problem characteristics.
        // For example, if demands are typically much smaller than distances,
        // the distance_contribution might need a smaller multiplier to balance its impact.
        // Here, 0.15f is a starting point for balancing.
        float score = demand_contribution + distance_contribution * 0.15f; // Tunable weight for distance

        // Add a small random perturbation to the score
        // (getRandomFractionFast() - 0.5f) generates a float in [-0.5, 0.5].
        // Multiplying by a very small factor ensures this perturbation is minor,
        // primarily acting as a tie-breaker for identical primary scores.
        score += (getRandomFractionFast() - 0.5f) * 0.001f; 

        // We want to sort in descending order of score (highest priority first),
        // so we store the negative of the score for use with std::sort (which sorts in ascending order).
        customer_scores.emplace_back(-score, customerId);
    }

    // Sort customers based on their calculated (negative) scores.
    // Since the number of removed customers is small, std::sort is very fast here.
    std::sort(customer_scores.begin(), customer_scores.end());

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}