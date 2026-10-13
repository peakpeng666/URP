#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

// Customer selection heuristic for Large Neighborhood Search.
// This heuristic aims to select a small number of customers that are somewhat geographically
// clustered, to encourage meaningful local changes during reinsertion, while incorporating
// stochasticity for diversity over many iterations.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selectedCustomers;
    std::unordered_set<int> selectedCustomerSet; // Used for O(1) checking if a customer is already selected

    // Determine the number of customers to remove, within a specified range (e.g., 10 to 20)
    int numCustomersToRemove = getRandomNumber(10, 20);

    // Phase 1: Select an initial random customer as the starting point for the removal cluster.
    // Customer IDs are assumed to be 1-indexed.
    int startCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.push_back(startCustomer);
    selectedCustomerSet.insert(startCustomer);

    // This vector holds customers from which we will consider expanding the selection.
    // It's initialized with the first selected customer.
    std::vector<int> expansionCandidates;
    expansionCandidates.push_back(startCustomer);

    // Phase 2: Iteratively expand the selected set by adding neighbors of already selected customers.
    while (selectedCustomers.size() < numCustomersToRemove) {
        // Fallback mechanism: If all current expansion candidates are exhausted (i.e., all their
        // closest neighbors are already selected), or if `expansionCandidates` somehow becomes empty,
        // pick a completely new random unselected customer. This prevents getting stuck and ensures
        // progress and diversity by potentially starting a new mini-cluster elsewhere.
        if (expansionCandidates.empty()) {
            int randomUnselectedCustomer = -1;
            int attempts = 0; 
            // Loop to find an unselected customer; limit attempts to prevent infinite loop
            do {
                randomUnselectedCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            } while (selectedCustomerSet.count(randomUnselectedCustomer) && attempts < sol.instance.numCustomers * 2);

            // If, after many attempts, we still cannot find an unselected customer (e.g., if
            // numCustomersToRemove is very large or all customers are already selected), break
            // and return the current set of selected customers.
            if (selectedCustomerSet.count(randomUnselectedCustomer)) {
                 break; 
            }

            selectedCustomers.push_back(randomUnselectedCustomer);
            selectedCustomerSet.insert(randomUnselectedCustomer);
            expansionCandidates.push_back(randomUnselectedCustomer); // Add the new customer as a potential expansion point
            continue; // Continue to the next iteration of the main while loop
        }

        // Randomly pick a pivot customer from the existing expansion candidates.
        // This introduces stochasticity in the expansion direction.
        int pivotIndex = getRandomNumber(0, expansionCandidates.size() - 1);
        int pivotCustomer = expansionCandidates[pivotIndex];

        // Access the pre-sorted list of neighbors by distance (from Instance.h).
        const auto& neighbors = sol.instance.adj[pivotCustomer];
        std::vector<int> potentialNeighbors;
        
        // Consider only a limited number of the closest neighbors to maintain a sense of locality
        // for the cluster of removed customers. This parameter can be tuned.
        int maxNeighborsToConsider = std::min((int)neighbors.size(), 15); 

        // Collect unselected neighbors from the closest ones of the pivot customer.
        for (int i = 0; i < maxNeighborsToConsider; ++i) {
            if (selectedCustomerSet.find(neighbors[i]) == selectedCustomerSet.end()) {
                potentialNeighbors.push_back(neighbors[i]);
            }
        }

        if (!potentialNeighbors.empty()) {
            // If unselected neighbors are found, randomly select one to add to the set.
            // This adds more stochasticity to the cluster formation.
            int chosenNeighbor = potentialNeighbors[getRandomNumber(0, potentialNeighbors.size() - 1)];
            selectedCustomers.push_back(chosenNeighbor);
            selectedCustomerSet.insert(chosenNeighbor);
            expansionCandidates.push_back(chosenNeighbor); // Add the newly selected customer as a new expansion point
        } else {
            // If the current pivot customer has no unselected neighbors among its closest ones,
            // remove it from the `expansionCandidates` list to avoid redundant checks in future iterations.
            // This is an efficient way to remove an element from a vector when order doesn't matter.
            std::swap(expansionCandidates[pivotIndex], expansionCandidates.back());
            expansionCandidates.pop_back();
        }
    }

    return selectedCustomers;
}

// Heuristic for ordering the removed customers before greedy reinsertion.
// This heuristic prioritizes customers with higher prizes (profitability)
// and adds a stochastic component to ensure diversity in ordering over millions of iterations.
// Note: This function does not have access to the `Solution` object to determine if a customer
// was previously served, so it relies solely on `Instance` data.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    struct CustomerSortInfo {
        int id;
        float score;
    };

    std::vector<CustomerSortInfo> sortableCustomers;

    // Determine the maximum prize value among all customers in the instance.
    // This value is used to scale the stochastic noise, ensuring it's relevant
    // but doesn't completely overshadow the actual prize.
    float maxPrizeValue = 0.0f;
    for(int i=1; i<=instance.numCustomers; ++i) {
        if (instance.prizes[i] > maxPrizeValue) {
            maxPrizeValue = instance.prizes[i];
        }
    }
    // Safety check to prevent division by zero or overly large noise if all prizes are zero.
    if (maxPrizeValue == 0.0f) maxPrizeValue = 1.0f; 

    // Calculate a score for each customer based on its prize and added stochastic noise.
    for (int customerId : customers) {
        float prize = instance.prizes[customerId];
        
        // Add stochastic noise (e.g., a random value between 0% and 10% of the max prize).
        // This small perturbation ensures that customers with very similar actual prize values
        // will have their relative order randomized across different LNS iterations, fostering
        // exploration.
        float noise = getRandomFractionFast() * 0.10f * maxPrizeValue;
        
        // The score combines the customer's prize with this stochastic noise.
        float score = prize + noise;
        sortableCustomers.push_back({customerId, score});
    }

    // Sort the customers based on their calculated score in descending order.
    // Customers with higher (prize + noise) values will be attempted for reinsertion first.
    std::sort(sortableCustomers.begin(), sortableCustomers.end(), [](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        return a.score > b.score;
    });

    // Update the original 'customers' vector with the newly sorted order.
    customers.clear();
    for (const auto& info : sortableCustomers) {
        customers.push_back(info.id);
    }
}