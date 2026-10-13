#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle
#include <limits>    // For std::numeric_limits

// Constants for customer selection heuristic
// Defines the minimum number of customers to remove in a single LNS iteration.
const int MIN_CUSTOMERS_TO_REMOVE = 10;
// Defines the maximum number of customers to remove in a single LNS iteration.
const int MAX_CUSTOMERS_TO_REMOVE = 25;
// Defines how many of the seed customer's nearest neighbors are initially considered as candidates for removal.
const int INITIAL_NEIGHBORS_FROM_SEED = 10;
// Defines how many of a newly selected customer's nearest neighbors are added to the candidate pool.
const int NEW_CUSTOMER_NEIGHBORS_TO_ADD = 5;

std::vector<int> select_by_llm_1(const Solution& sol) {
    static thread_local std::mt19937 gen(std::random_device{}());

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidateCustomersVec;
    std::unordered_set<int> candidateCustomersSet;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (sol.instance.numCustomers == 0 || numCustomersToRemove <= 0) {
        return {};
    }

    // 1. Select a random seed customer to start the removal cluster.
    // Customer IDs are 1-indexed, so ensure getRandomNumber reflects this range.
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);

    // 2. Add a few of the seed customer's nearest neighbors to the candidate pool.
    // The `adj` list is 0-indexed where index 0 is the depot, so customer 'c' is at `adj[c]`.
    if (seedCustomer < (int)sol.instance.adj.size()) { // Check bounds for adj list access
        for (int neighbor : sol.instance.adj[seedCustomer]) {
            if ((int)candidateCustomersVec.size() >= INITIAL_NEIGHBORS_FROM_SEED) {
                break;
            }
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() &&
                candidateCustomersSet.find(neighbor) == candidateCustomersSet.end()) {
                candidateCustomersVec.push_back(neighbor);
                candidateCustomersSet.insert(neighbor);
            }
        }
    }

    // 3. Iteratively expand the selection until the target number of customers to remove is reached.
    while ((int)selectedCustomersSet.size() < numCustomersToRemove) {
        int customerToSelect = -1;

        if (!candidateCustomersVec.empty()) {
            // Pick a random customer from the current candidates to add to the selected set.
            int randIdx = getRandomNumber(0, (int)candidateCustomersVec.size() - 1);
            customerToSelect = candidateCustomersVec[randIdx];

            // Remove the selected customer from the candidate pool efficiently.
            candidateCustomersVec[randIdx] = candidateCustomersVec.back();
            candidateCustomersVec.pop_back();
            candidateCustomersSet.erase(customerToSelect);

            // If this customer was already selected (e.g., via another path in the cluster growth), skip and try again.
            if (selectedCustomersSet.count(customerToSelect)) {
                continue;
            }
        } else {
            // Fallback: If the candidate pool becomes empty (e.g., all local neighbors exhausted or selected),
            // pick a completely random unselected customer to ensure `numCustomersToRemove` is met.
            do {
                customerToSelect = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.count(customerToSelect));
        }

        selectedCustomersSet.insert(customerToSelect);

        // Add a few of the newly selected customer's nearest neighbors to the candidate pool for further expansion.
        if (customerToSelect < (int)sol.instance.adj.size()) { // Check bounds
            int neighborsAdded = 0;
            for (int neighbor : sol.instance.adj[customerToSelect]) {
                if (neighborsAdded >= NEW_CUSTOMER_NEIGHBORS_TO_ADD) {
                    break;
                }
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() &&
                    candidateCustomersSet.find(neighbor) == candidateCustomersSet.end()) {
                    candidateCustomersVec.push_back(neighbor);
                    candidateCustomersSet.insert(neighbor);
                    neighborsAdded++;
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());

    if (customers.empty()) {
        return;
    }

    std::vector<int> sortedCustomers;
    std::unordered_set<int> remainingCustomersSet(customers.begin(), customers.end());

    // Stochasticity: Choose a random starting customer from the list to be sorted.
    int currentCustomerIndexInCustomersList = getRandomNumber(0, (int)customers.size() - 1);
    int currentCustomer = customers[currentCustomerIndexInCustomersList];

    sortedCustomers.push_back(currentCustomer);
    remainingCustomersSet.erase(currentCustomer);

    // Sort the remaining customers using a Nearest Neighbor (TSP-like) heuristic.
    while (!remainingCustomersSet.empty()) {
        int nextCustomerToAdd = -1;

        // Try to find the nearest remaining customer using the pre-sorted adjacency list.
        if (currentCustomer < (int)instance.adj.size()) { // Check bounds for adj list access
            for (int neighbor : instance.adj[currentCustomer]) {
                if (remainingCustomersSet.count(neighbor)) {
                    nextCustomerToAdd = neighbor;
                    break; // Found the nearest remaining customer
                }
            }
        }

        // Fallback: If no nearby remaining customer is found via the adjacency list (e.g., `adj` list is limited,
        // or all immediate neighbors are already sorted), pick an arbitrary customer from the remaining set.
        // `unordered_set::begin()` provides an iterator to an element in O(1) time. Its order is not guaranteed,
        // which implicitly adds some stochasticity.
        if (nextCustomerToAdd == -1) {
            nextCustomerToAdd = *remainingCustomersSet.begin();
        }

        currentCustomer = nextCustomerToAdd;
        sortedCustomers.push_back(currentCustomer);
        remainingCustomersSet.erase(currentCustomer);
    }

    customers = sortedCustomers;
}