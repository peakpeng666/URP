#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric> // For std::iota if needed, but not for this design
#include "Utils.h"

// Parameters for customer selection
const int MIN_CUSTOMERS_TO_REMOVE = 15;
const int MAX_CUSTOMERS_TO_REMOVE = 30;
const int MAX_NEIGHBORS_TO_CONSIDER = 10; // When expanding selection, only consider this many closest neighbors
const float PROB_ACCEPT_NEIGHBOR = 0.9f;   // Probability to accept a candidate neighbor into the selection


// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidatesForExpansion; // Stores customers already selected, from which we can find more neighbors

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int currentSourceCustomer = -1;

        if (candidatesForExpansion.empty()) {
            // No current cluster or ran out of candidates from previous cluster, pick a new random seed
            int randomSeed = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomers.find(randomSeed) == selectedCustomers.end()) {
                selectedCustomers.insert(randomSeed);
                candidatesForExpansion.push_back(randomSeed);
                if (selectedCustomers.size() == numCustomersToRemove) break;
            } else {
                continue; // Try picking another random seed if already selected
            }
        } else {
            // Pick a random customer from the existing selected cluster to expand from
            int sourceIdx = getRandomNumber(0, candidatesForExpansion.size() - 1);
            currentSourceCustomer = candidatesForExpansion[sourceIdx];
            // To ensure diversity and avoid getting stuck, remove this source customer if it doesn't yield new customers
            // This is handled by removing it from candidatesForExpansion later if no new customer is added
        }

        bool addedNewCustomer = false;
        if (currentSourceCustomer != -1) {
            const std::vector<int>& neighbors = sol.instance.adj[currentSourceCustomer];
            int numNeighborsToCheck = std::min((int)neighbors.size(), MAX_NEIGHBORS_TO_CONSIDER);

            for (int i = 0; i < numNeighborsToCheck; ++i) {
                int neighborCustomer = neighbors[i];
                if (selectedCustomers.find(neighborCustomer) == selectedCustomers.end()) {
                    if (getRandomFraction() < PROB_ACCEPT_NEIGHBOR) {
                        selectedCustomers.insert(neighborCustomer);
                        candidatesForExpansion.push_back(neighborCustomer);
                        addedNewCustomer = true;
                        break; // Added one, move to next main loop iteration
                    }
                }
            }

            if (!addedNewCustomer) {
                // If the currentSourceCustomer did not help in finding new customers, remove it
                // from candidatesForExpansion to avoid repeatedly trying it.
                // Find and remove it from vector (inefficient, but for small `candidatesForExpansion` size, it's fine).
                // A better approach would be to use a std::list or keep a vector and shuffle/remove at end.
                // For simplicity and speed given expected small size:
                for(size_t i = 0; i < candidatesForExpansion.size(); ++i) {
                    if (candidatesForExpansion[i] == currentSourceCustomer) {
                        candidatesForExpansion.erase(candidatesForExpansion.begin() + i);
                        break;
                    }
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Structure to hold customer data for sorting
struct CustomerSortData {
    int customerId;
    float twWidth;
    int demand;
    float distToDepot;
    float perturbation; // For stochastic sorting
};

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<CustomerSortData> sortData;
    sortData.reserve(customers.size());

    for (int customerId : customers) {
        CustomerSortData data;
        data.customerId = customerId;
        data.twWidth = instance.TW_Width[customerId];
        data.demand = instance.demand[customerId];
        data.distToDepot = instance.distanceMatrix[0][customerId]; // Distance from depot (node 0)
        data.perturbation = getRandomFractionFast() * 0.001f; // Small random noise for stochasticity

        sortData.push_back(data);
    }

    // Sort based on multiple criteria:
    // 1. Time Window Width (ascending): Tighter windows first (harder to place)
    // 2. Demand (descending): Higher demand first (harder to fit capacity)
    // 3. Distance to Depot (descending): Farthest customers first (might create more impactful initial placements)
    // 4. Perturbation: Ensures diversity when other values are equal
    std::sort(sortData.begin(), sortData.end(), [&](const CustomerSortData& a, const CustomerSortData& b) {
        if (a.twWidth + a.perturbation != b.twWidth + b.perturbation) {
            return a.twWidth + a.perturbation < b.twWidth + b.perturbation;
        }
        if (a.demand + a.perturbation != b.demand + b.perturbation) {
            return a.demand + a.perturbation > b.demand + b.perturbation;
        }
        return a.distToDepot + a.perturbation > b.distToDepot + b.perturbation;
    });

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sortData[i].customerId;
    }
}