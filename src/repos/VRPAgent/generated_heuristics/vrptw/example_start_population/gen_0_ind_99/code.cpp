#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove.
    // The range 10-25 provides a balance between local search intensity and diversity.
    int numCustomersToRemove = getRandomNumber(10, 25);

    std::unordered_set<int> selectedCustomers;
    // expansionFrontier stores selected customers that still have unselected neighbors.
    // We expand the set of removed customers by picking from this frontier.
    std::vector<int> expansionFrontier;

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    // Step 1: Pick an initial seed customer randomly.
    // Customer IDs are typically 1-indexed.
    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeedCustomer);
    expansionFrontier.push_back(initialSeedCustomer);

    // Step 2: Expand the set of selected customers until the target number is reached.
    // This process ensures that each selected customer is close to at least one other selected customer.
    while (selectedCustomers.size() < numCustomersToRemove) {
        // If the expansion frontier is empty, it means all customers reachable from the initial seed(s)
        // have been selected or exhausted. We cannot add more customers while maintaining the
        // "close to at least one other selected customer" property. Thus, we break and return
        // the current set, which might be smaller than numCustomersToRemove.
        if (expansionFrontier.empty()) {
            break;
        }

        // Randomly pick a customer from the expansion frontier to attempt to expand from.
        // This introduces stochasticity in the expansion path.
        int randIdx = getRandomNumber(0, expansionFrontier.size() - 1);
        int currentExpansionCustomer = expansionFrontier[randIdx];

        std::vector<int> potentialNewCustomers;
        // Access neighbors using the customer ID directly, as it typically corresponds to the node ID.
        // E.g., for customer ID 'c', its node ID is also 'c'.
        const auto& neighbors = sol.instance.adj[currentExpansionCustomer];

        for (int neighborNodeId : neighbors) {
            int neighborCustomerId = neighborNodeId; // Neighbor node ID is also its customer ID if > 0.

            // Ensure the neighbor is a customer (not the depot, i.e., ID >= 1)
            // and has not been selected yet.
            if (neighborCustomerId >= 1 && selectedCustomers.find(neighborCustomerId) == selectedCustomers.end()) {
                potentialNewCustomers.push_back(neighborCustomerId);
            }
        }

        if (potentialNewCustomers.empty()) {
            // If the chosen 'currentExpansionCustomer' has no unselected neighbors,
            // remove it from the frontier, as it can no longer be used for expansion.
            expansionFrontier.erase(expansionFrontier.begin() + randIdx);
            continue; // Try again with another customer from the frontier.
        }

        // Pick a random customer from the list of potential new customers to add.
        // This adds further stochasticity.
        int newCustomer = potentialNewCustomers[getRandomNumber(0, potentialNewCustomers.size() - 1)];
        selectedCustomers.insert(newCustomer);
        // The newly added customer is now also part of the expansion frontier, as it might have unselected neighbors.
        expansionFrontier.push_back(newCustomer);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // We will sort customers based on a "priority score".
    // A vector of pairs (score, customer_id) is used for sorting.
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    // Calculate a score for each customer to determine reinsertion order.
    for (int customerId : customers) {
        // Primary criterion: Time Window Width (TW_Width).
        // Customers with smaller TW_Width (tighter windows) are generally harder to place.
        // Placing them earlier in the reinsertion process might lead to better solutions
        // as they constrain the available options more significantly.
        // Customer ID is directly used as node ID for accessing instance data.
        float score = instance.TW_Width[customerId];

        // Add a small random perturbation to the score.
        // This introduces stochasticity, breaking ties for customers with similar TW_Width
        // and ensuring diversity across millions of iterations without significantly altering the primary order.
        score += getRandomFractionFast() * 1e-6; // A very small random float in [0, 1e-6)

        customerScores.push_back({score, customerId});
    }

    // Sort customers based on their calculated scores in ascending order.
    // Customers with tighter time windows (smaller scores) will be placed first.
    std::sort(customerScores.begin(), customerScores.end());

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}