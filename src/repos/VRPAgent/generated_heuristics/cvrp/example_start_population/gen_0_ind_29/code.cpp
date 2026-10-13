#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits>
#include "Utils.h"

// Constants for customer selection
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;
const float PROB_EXPAND_FROM_EXISTING = 0.85f; // Probability to select a neighbor of an already selected customer
const int MAX_NEIGHBORS_TO_CONSIDER = 100; // Limit search for neighbors to top N closest

// Constants for customer ordering
const int K_CLOSEST_REMOVED_FOR_SORT = 3; // Consider K closest *other removed* customers for sorting score
// Weights for sorting score (adjust as needed to prioritize factors)
const float WEIGHT_CLUSTERING = 1000.0f;
const float WEIGHT_DEMAND = 1.0f;
const float WEIGHT_DIST_DEPOT = 0.1f;


// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidateExpansionCustomers;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    // Initial seed customers
    if (sol.instance.numCustomers > 0) {
        int initialCustomer1 = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomers.insert(initialCustomer1);
        candidateExpansionCustomers.push_back(initialCustomer1);
    }

    // Iteratively select more customers
    while (selectedCustomers.size() < numCustomersToRemove) {
        float r = getRandomFractionFast();
        int customerToAdd = -1;

        if (r < PROB_EXPAND_FROM_EXISTING && !candidateExpansionCustomers.empty()) {
            // Option A: Expand from an existing selected customer
            int maxAttempts = 50; // Limit attempts to find a neighbor
            int attempts = 0;
            while (attempts < maxAttempts && customerToAdd == -1) {
                int originIdx = getRandomNumber(0, (int)candidateExpansionCustomers.size() - 1);
                int cOrigin = candidateExpansionCustomers[originIdx];

                int numNeighborsToTry = std::min((int)sol.instance.adj[cOrigin].size(), MAX_NEIGHBORS_TO_CONSIDER);
                if (numNeighborsToTry > 0) {
                    int neighborAttempts = 0;
                    while (neighborAttempts < numNeighborsToTry && customerToAdd == -1) {
                        int neighborIdx = getRandomNumber(0, numNeighborsToTry - 1);
                        int neighborNode = sol.instance.adj[cOrigin][neighborIdx];

                        // Ensure it's a customer and not already selected
                        if (neighborNode >= 1 && neighborNode <= sol.instance.numCustomers &&
                            selectedCustomers.find(neighborNode) == selectedCustomers.end()) {
                            customerToAdd = neighborNode;
                        }
                        neighborAttempts++;
                    }
                }
                attempts++;
            }
        }

        if (customerToAdd == -1) {
            // Option B or fallback: Pick a completely random customer
            int cRand = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.find(cRand) != selectedCustomers.end()) {
                cRand = getRandomNumber(1, sol.instance.numCustomers);
            }
            customerToAdd = cRand;
        }

        if (customerToAdd != -1) {
            selectedCustomers.insert(customerToAdd);
            candidateExpansionCustomers.push_back(customerToAdd);
        } else {
            // Fallback in case no customer could be selected after many attempts
            // This should rarely happen if numCustomersToRemove is small relative to total customers
            break;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;

    for (int customer_id : customers) {
        float current_demand = instance.demand[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id];

        std::vector<float> distances_to_other_removed;
        for (int other_customer_id : customers) {
            if (other_customer_id != customer_id) {
                distances_to_other_removed.push_back(instance.distanceMatrix[customer_id][other_customer_id]);
            }
        }

        float closeness_to_removed_score = 0.0f;
        if (!distances_to_other_removed.empty()) {
            std::sort(distances_to_other_removed.begin(), distances_to_other_removed.end());
            int count_to_sum = std::min((int)distances_to_other_removed.size(), K_CLOSEST_REMOVED_FOR_SORT);
            for (int i = 0; i < count_to_sum; ++i) {
                closeness_to_removed_score += distances_to_other_removed[i];
            }
        } else {
            // If only one customer removed, or this is the only one in the list, its closeness to removed is irrelevant
            // Set to a value that doesn't influence primary sort much, or makes it an outlier
            closeness_to_removed_score = std::numeric_limits<float>::max();
        }

        // Combine factors into a score. Lower score means higher priority for reinsertion.
        // We want customers that are more clustered among removed ones (lower closeness_to_removed_score) to be first.
        // Then, smaller demand and closer to depot.
        float score = (closeness_to_removed_score * WEIGHT_CLUSTERING) +
                      (current_demand * WEIGHT_DEMAND) +
                      (dist_to_depot * WEIGHT_DIST_DEPOT);

        // Add a small random noise to ensure diversity in sorting for identical scores
        score += getRandomFractionFast() * 0.001f;

        scored_customers.push_back({score, customer_id});
    }

    // Sort based on the calculated score in ascending order
    std::sort(scored_customers.begin(), scored_customers.end());

    // Update the input customers vector with the sorted customer IDs
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}