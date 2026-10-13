#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::min, std::reverse
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast, argsort

// Thread-local random number generator for stochasticity
static thread_local std::mt19937 gen(std::random_device{}());

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20); // Number of customers to remove

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList; // To maintain insertion order for seed selection

    // 1. Select an initial random seed customer
    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersList.push_back(initialCustomer);

    int attempts = 0; // Counter to prevent getting stuck if a cluster cannot easily grow

    // 2. Iteratively select customers based on proximity to already selected ones
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int nextCustomer = -1;

        // Try to pick a new customer close to an existing selected customer
        // Shuffle the list of selected customers to get varied starting points for cluster expansion
        std::shuffle(selectedCustomersList.begin(), selectedCustomersList.end(), gen);

        for (int seedCustomer : selectedCustomersList) {
            // Check a limited number of closest neighbors
            int numNeighborsToCheck = std::min((int)sol.instance.adj[seedCustomer].size(), 10 + getRandomNumber(0, 5)); // Check 10-15 closest neighbors

            for (int i = 0; i < numNeighborsToCheck; ++i) {
                int neighbor = sol.instance.adj[seedCustomer][i];
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) { // If neighbor not already selected
                    // Introduce stochasticity: pick this neighbor with a certain probability
                    if (getRandomFractionFast() < 0.8) { // 80% chance to select a valid neighbor
                        nextCustomer = neighbor;
                        break; // Found a suitable neighbor, break inner loop
                    }
                }
            }
            if (nextCustomer != -1) {
                break; // Found a suitable neighbor, break outer loop (from seedCustomer iteration)
            }
        }

        // 3. Fallback: If no suitable neighbor found or too many attempts, pick a random unselected customer
        if (nextCustomer == -1 || attempts > 2 * numCustomersToRemove) {
            do {
                nextCustomer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.find(nextCustomer) != selectedCustomersSet.end());
            attempts = 0; // Reset attempts after fallback
        } else {
            attempts++; // Increment attempts if still trying to find a close neighbor
        }

        selectedCustomersSet.insert(nextCustomer);
        selectedCustomersList.push_back(nextCustomer); // Add to list for future seed selection
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float selector = getRandomFractionFast();
    std::vector<float> values;
    values.reserve(customers.size());

    // Probabilistically choose a sorting strategy
    if (selector < 0.4) { // 40% chance: Sort by Prize/Demand Ratio (Descending)
        for (int c : customers) {
            values.push_back(instance.prizes[c] / (instance.demand[c] + 1e-6)); // Add small epsilon to avoid division by zero
        }
        std::vector<int> sorted_indices = argsort(values);
        std::reverse(sorted_indices.begin(), sorted_indices.end()); // For descending order

        std::vector<int> temp_customers;
        temp_customers.reserve(customers.size());
        for (int idx : sorted_indices) {
            temp_customers.push_back(customers[idx]);
        }
        customers = temp_customers;

    } else if (selector < 0.7) { // 30% chance: Sort by Distance to Depot (Ascending)
        for (int c : customers) {
            values.push_back(instance.distanceMatrix[0][c]);
        }
        std::vector<int> sorted_indices = argsort(values); // argsort gives ascending order

        std::vector<int> temp_customers;
        temp_customers.reserve(customers.size());
        for (int idx : sorted_indices) {
            temp_customers.push_back(customers[idx]);
        }
        customers = temp_customers;

    } else if (selector < 0.9) { // 20% chance: Sort by Prize Value (Descending)
        for (int c : customers) {
            values.push_back(instance.prizes[c]);
        }
        std::vector<int> sorted_indices = argsort(values);
        std::reverse(sorted_indices.begin(), sorted_indices.end()); // For descending order

        std::vector<int> temp_customers;
        temp_customers.reserve(customers.size());
        for (int idx : sorted_indices) {
            temp_customers.push_back(customers[idx]);
        }
        customers = temp_customers;

    } else { // 10% chance: Random Shuffle
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}