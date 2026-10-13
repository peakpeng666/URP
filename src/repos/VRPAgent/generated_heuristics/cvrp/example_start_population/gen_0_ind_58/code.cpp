#include <random>
#include <vector>
#include <unordered_set>
#include <algorithm> // For std::sort

// Assuming AgentDesigned.h implicitly or explicitly includes:
// "Solution.h"
// "Tour.h"
// "Instance.h"
// "Utils.h"
// If not, these would need to be directly included here.

// Constants for select_by_llm_1
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 25; // Adjusted range from original 10-20 for more diversity
const int SELECTION_ATTEMPTS_PER_CUSTOMER = 100; // Attempts to find a connected customer before falling back to random

// Constants for sort_by_llm_1
const float SORT_DEMAND_WEIGHT = 1.0f;     // Weight for customer demand
const float SORT_DEGREE_WEIGHT = 0.5f;     // Weight for customer's degree (number of neighbors in adj list)
const float SORT_NOISE_MAGNITUDE = 0.1f;   // Magnitude of random noise to add to sorting scores


// Customer selection heuristic for Large Neighborhood Search (LNS)
// Selects a subset of customers to remove from the current solution.
// The heuristic aims to select customers that are mostly spatially connected,
// ensuring meaningful changes during reinsertion, while incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList; // Used for efficient random access to already selected customers

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    // Step 1: Select an initial random customer to start the removal cluster.
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersList.push_back(initialCustomer);

    // Step 2: Iteratively select additional customers.
    // Prioritize customers that are neighbors of already selected ones to encourage spatial connectivity.
    // A fallback to a completely random unselected customer is used if no connected customer can be found
    // after a certain number of attempts, ensuring the target number of customers is always reached.
    while (selectedCustomersList.size() < numCustomersToRemove) {
        bool addedConnectedCustomer = false;
        
        // Attempt to find and add a neighbor of an already selected customer.
        for (int attempt = 0; attempt < SELECTION_ATTEMPTS_PER_CUSTOMER; ++attempt) {
            // Randomly pick one customer from the list of already selected customers.
            int referenceCustomerIdx = getRandomNumber(0, selectedCustomersList.size() - 1);
            int referenceCustomer = selectedCustomersList[referenceCustomerIdx];

            const auto& neighbors = sol.instance.adj[referenceCustomer];
            if (neighbors.empty()) {
                continue; // This reference customer has no listed neighbors, try another reference.
            }

            // Randomly pick a neighbor from the reference customer's adjacency list.
            int neighborIdx = getRandomNumber(0, neighbors.size() - 1);
            int candidateCustomer = neighbors[neighborIdx];

            // Check if the candidate customer is valid and not already selected.
            // Customer IDs are typically 1-indexed, so check bounds.
            if (candidateCustomer >= 1 && candidateCustomer <= sol.instance.numCustomers &&
                selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(candidateCustomer);
                selectedCustomersList.push_back(candidateCustomer);
                addedConnectedCustomer = true;
                break; // Successfully added a connected customer, proceed to next iteration of the outer loop.
            }
        }

        // Fallback: If after several attempts, no new connected customer could be added (e.g., all neighbors
        // of selected customers are already selected, or picked bad reference customers repeatedly),
        // add a completely random unselected customer to ensure progress and meet the target count.
        if (!addedConnectedCustomer) {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomersSet.count(randomCustomer) > 0) {
                randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomersSet.insert(randomCustomer);
            selectedCustomersList.push_back(randomCustomer);
        }
    }

    return selectedCustomersList;
}

// Ordering heuristic for the removed customers in Large Neighborhood Search (LNS).
// This function sorts the customers that have been removed, determining the order
// in which they will be reinserted into the solution during the greedy reinsertion phase.
// The sorting aims to prioritize customers that might be more "critical" or "constraining"
// to place first, while also introducing stochasticity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Create a temporary vector to store (score, customer_id) pairs.
    // This allows sorting based on score while retaining the original customer IDs.
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = 0.0f;

        // Factor 1: Customer Demand
        // Higher demand customers might be more difficult to fit into vehicle capacities,
        // so prioritizing them early might lead to better overall placements.
        score += (float)instance.demand[customerId] * SORT_DEMAND_WEIGHT;

        // Factor 2: Customer Degree (number of neighbors in adjacency list)
        // Customers with more connections (higher degree) might be more central or critical
        // for forming efficient clusters/routes. Prioritizing them could establish core route structures.
        score += (float)instance.adj[customerId].size() * SORT_DEGREE_WEIGHT;

        // Factor 3: Stochastic Noise
        // Adding a small random perturbation to the score ensures diversity across millions of iterations.
        // It helps escape local optima by slightly altering the insertion order of customers with similar scores.
        score += getRandomFractionFast() * SORT_NOISE_MAGNITUDE;

        customerScores.emplace_back(score, customerId);
    }

    // Sort the customers in descending order based on their calculated score.
    // Customers with higher scores (e.g., higher demand, more connections) will appear first in the sorted list.
    std::sort(customerScores.begin(), customerScores.end(),
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}