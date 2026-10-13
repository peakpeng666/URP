#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include <limits>    // For numeric_limits
#include "Utils.h"   // For getRandomNumber, getRandomFraction

// Heuristic for selecting customers to remove
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    // Cap the number of customers to remove at the total number of customers
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    if (numCustomersToRemove == 0) {
        return {};
    }

    // Step 1: Initial Seed - Pick a random customer to start the removal process.
    // We choose from all customers (1 to numCustomers) because unvisited customers
    // may also need to be "selected" to be considered for reinsertion.
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialCustomer);

    // Step 2: Iterative Expansion - Grow the set of selected customers by prioritizing neighbors.
    // This helps ensure selected customers are "close to at least one or a few other selected customers".
    static thread_local std::mt19937 gen(std::random_device{}()); // For std::shuffle

    while (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> candidatesToExpandFrom;
        for (int c_s : selectedCustomers) {
            candidatesToExpandFrom.push_back(c_s);
        }

        // Shuffle the list of customers already selected. This adds diversity
        // by changing which "cluster" or "chain" we try to expand from next.
        std::shuffle(candidatesToExpandFrom.begin(), candidatesToExpandFrom.end(), gen);

        bool foundNew = false;
        for (int c_pivot : candidatesToExpandFrom) {
            std::vector<int> unselectedNeighbors;
            for (int neighbor : sol.instance.adj[c_pivot]) {
                if (neighbor == 0) continue; // Skip the depot
                if (selectedCustomers.count(neighbor) == 0) { // If neighbor is not already selected
                    unselectedNeighbors.push_back(neighbor);
                }
            }

            if (!unselectedNeighbors.empty()) {
                // Pick a random unselected neighbor from the list
                selectedCustomers.insert(unselectedNeighbors[getRandomNumber(0, unselectedNeighbors.size() - 1)]);
                foundNew = true;
                break; // Found and added a new customer, break from iterating candidatesToExpandFrom
            }
        }

        // Fallback: If no more unselected neighbors can be found from any of the currently selected customers,
        // pick a completely random unselected customer to ensure the target number is reached.
        if (!foundNew) {
            std::vector<int> unselectedCustomers;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomers.count(i) == 0) {
                    unselectedCustomers.push_back(i);
                }
            }
            if (unselectedCustomers.empty()) {
                // This case should ideally not be reached if numCustomersToRemove is less than total customers
                break;
            }
            selectedCustomers.insert(unselectedCustomers[getRandomNumber(0, unselectedCustomers.size() - 1)]);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Heuristic for ordering the removed customers for greedy reinsertion
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_values;
    customer_values.reserve(customers.size());

    // Calculate a "value" for each customer, prioritizing high prize for low demand.
    // This heuristic aims to reinsert more "valuable" customers first, hoping to secure their inclusion.
    for (int customer_id : customers) {
        float prize = instance.prizes[customer_id];
        int demand = instance.demand[customer_id];
        float value;

        if (demand == 0) {
            if (prize > 0) {
                // Very high value for customers with prize but no demand (effectively free prize)
                value = std::numeric_limits<float>::max();
            } else {
                // Very low value for customers with no prize and no demand (less useful to collect)
                value = std::numeric_limits<float>::lowest();
            }
        } else {
            // Standard prize-to-demand ratio
            value = prize / static_cast<float>(demand);
        }
        customer_values.push_back({value, customer_id});
    }

    // Sort customers in descending order based on their calculated value
    std::sort(customer_values.begin(), customer_values.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Copy the sorted customer IDs back to the original vector
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_values[i].second;
    }

    // Introduce stochasticity: Perform random adjacent swaps with a low probability.
    // This helps diversify the order over millions of iterations without completely
    // destroying the value-based sorting.
    float swap_probability = 0.05f; // 5% chance to swap adjacent elements
    for (size_t i = 0; i < customers.size() - 1; ++i) {
        if (getRandomFraction() < swap_probability) {
            std::swap(customers[i], customers[i + 1]);
        }
    }
}