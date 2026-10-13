#include "AgentDesigned.h"
#include <vector>
#include <unordered_set>
#include <algorithm> // For std::sort and std::min
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 25;
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // Seed the removal process with an initial random customer
    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialSeedCustomer);
    selectedCustomersList.push_back(initialSeedCustomer);

    // Iteratively expand the set of selected customers
    // This creates a "cluster" or several small "clusters" of removed customers.
    // A fail-safe mechanism ensures progress even if cluster expansion stalls.
    int consecutiveFailedExpansions = 0;
    int maxConsecutiveFailuresBeforeRandom = 5; // After this many failures, force a random unselected customer

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool addedCustomerThisIteration = false;

        // Attempt to expand the cluster from an existing selected customer
        if (consecutiveFailedExpansions < maxConsecutiveFailuresBeforeRandom && !selectedCustomersList.empty()) {
            int sourceCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];
            const std::vector<int>& neighbors = sol.instance.adj[sourceCustomer];
            std::vector<int> potentialNewCustomers;
            int numNeighborsToConsider = std::min((int)neighbors.size(), 15); // Limit search for speed

            for (int i = 0; i < numNeighborsToConsider; ++i) {
                int candidateCustomer = neighbors[i];
                if (candidateCustomer > 0 && selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
                    potentialNewCustomers.push_back(candidateCustomer);
                }
            }

            if (!potentialNewCustomers.empty()) {
                int newCustomer = potentialNewCustomers[getRandomNumber(0, potentialNewCustomers.size() - 1)];
                selectedCustomersSet.insert(newCustomer);
                selectedCustomersList.push_back(newCustomer);
                addedCustomerThisIteration = true;
                consecutiveFailedExpansions = 0; // Reset counter on success
            }
        }

        if (!addedCustomerThisIteration) {
            consecutiveFailedExpansions++;
            // If cluster expansion failed or max consecutive failures reached,
            // force add a new random unselected customer to ensure progress and diversity
            if (selectedCustomersSet.size() < sol.instance.numCustomers) {
                int newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                while (selectedCustomersSet.find(newRandomCustomer) != selectedCustomersSet.end() && selectedCustomersSet.size() < sol.instance.numCustomers) {
                    newRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                }
                if (selectedCustomersSet.find(newRandomCustomer) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(newRandomCustomer);
                    selectedCustomersList.push_back(newRandomCustomer);
                    consecutiveFailedExpansions = 0; // Reset counter
                } else {
                    // All remaining customers are already selected. Break loop.
                    break;
                }
            } else {
                // All customers are selected, and numCustomersToRemove not reached. Break loop.
                break;
            }
        }
    }
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    struct CustomerSortInfo {
        int id;
        float time_window_width;
        float demand;
        float service_time;
        float random_tie_breaker;
    };

    std::vector<CustomerSortInfo> sort_data;
    for (int cust_id : customers) {
        sort_data.push_back({
            cust_id,
            instance.TW_Width[cust_id],
            static_cast<float>(instance.demand[cust_id]),
            instance.serviceTime[cust_id],
            getRandomFractionFast()
        });
    }

    std::sort(sort_data.begin(), sort_data.end(), [&](const CustomerSortInfo& a, const CustomerSortInfo& b) {
        // Handle potential zero time window width to avoid division by zero or large floats
        float tw_a_norm = (a.time_window_width > 0) ? a.time_window_width : 0.00001f;
        float tw_b_norm = (b.time_window_width > 0) ? b.time_window_width : 0.00001f;

        // Priority 1: Customers with tighter time windows first (smaller TW_Width)
        if (tw_a_norm != tw_b_norm) {
            return tw_a_norm < tw_b_norm;
        }
        // Priority 2: Customers with higher demand first
        if (a.demand != b.demand) {
            return a.demand > b.demand;
        }
        // Priority 3: Customers with longer service time first
        if (a.service_time != b.service_time) {
            return a.service_time > b.service_time;
        }
        // Priority 4: Random tie-breaker for identical values to ensure stochasticity
        return a.random_tie_breaker < b.random_tie_breaker;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data[i].id;
    }
}