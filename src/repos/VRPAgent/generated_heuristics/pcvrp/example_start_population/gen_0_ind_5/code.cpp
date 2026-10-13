#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::find, std::shuffle, std::min
#include <vector>    // For std::vector
#include "Utils.h"

// New heuristic for customer selection
// This heuristic aims to select a small, "connected-ish" group of customers
// for removal, prioritizing those geographically close or linked by existing tours.
// It incorporates stochastic behavior to ensure diversity across iterations.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList; // To store the final ordered list of selected customers

    // A pool of customers whose neighbors (geographical or tour-based) will be considered
    // for adding to the 'selectedCustomersSet'. This drives the "connected-ish" expansion.
    std::vector<int> expansionCandidates;

    // Determine the number of customers to remove stochastically
    int numCustomersToRemove = getRandomNumber(5, 25);

    // Safety check: ensure we don't try to remove more customers than available
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // 1. Seed selection: Pick an initial random customer to start the removal process.
    // This customer can be visited or unvisited.
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersList.push_back(seedCustomer);
    expansionCandidates.push_back(seedCustomer);

    // 2. Expand the set of selected customers until the target `numCustomersToRemove` is met.
    while (selectedCustomersList.size() < numCustomersToRemove) {
        if (expansionCandidates.empty()) {
            // Fallback: If the current "connected" pool of `expansionCandidates` is exhausted
            // (e.g., all neighbors explored or already selected), pick a completely random
            // unselected customer to continue. This ensures we always reach `numCustomersToRemove`
            // and can start a new small "mini-cluster" if the initial one was isolated.
            int fallbackCustomer = -1;
            int attempts = 0;
            // Limit attempts to prevent infinite loops on very small or unusual instances
            const int maxAttempts = sol.instance.numCustomers * 2; 
            do {
                fallbackCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            } while (selectedCustomersSet.count(fallbackCustomer) && attempts < maxAttempts);

            if (fallbackCustomer != -1 && !selectedCustomersSet.count(fallbackCustomer)) {
                selectedCustomersSet.insert(fallbackCustomer);
                selectedCustomersList.push_back(fallbackCustomer);
                expansionCandidates.push_back(fallbackCustomer); // Add to candidates for future expansion
            } else {
                // This scenario means we genuinely can't find enough unique customers,
                // which should be rare for large instances. Break to prevent infinite loop.
                break; 
            }
        }

        // Pick a random customer from the `expansionCandidates` pool.
        // This customer will serve as the "source" for finding new neighbors to add.
        int sourceCustomerIdx = getRandomNumber(0, expansionCandidates.size() - 1);
        int sourceCustomer = expansionCandidates[sourceCustomerIdx];
        
        // Remove the source customer from `expansionCandidates`. This prevents re-processing
        // its neighbors in the same selection phase and makes `expansionCandidates`
        // behave somewhat like a queue/stack for exploration.
        expansionCandidates.erase(expansionCandidates.begin() + sourceCustomerIdx);

        // Collect potential new neighbors for the `sourceCustomer`.
        std::vector<int> currentNeighborsToConsider;

        // Add geographical neighbors from the adjacency list (`instance.adj`).
        // The `adj` list is assumed to be sorted by distance, so picking from the beginning
        // ensures geographical proximity. We stochastically choose how many closest neighbors to consider.
        int numAdjNeighborsToConsider = std::min((int)sol.instance.adj[sourceCustomer].size(), getRandomNumber(3, 8));
        for (int i = 0; i < numAdjNeighborsToConsider; ++i) {
            currentNeighborsToConsider.push_back(sol.instance.adj[sourceCustomer][i]);
        }

        // Add tour neighbors if the `sourceCustomer` is currently part of an existing tour.
        // These are the customers immediately preceding and succeeding `sourceCustomer` in its tour.
        int tourIdx = sol.customerToTourMap[sourceCustomer];
        if (tourIdx != -1) { // -1 means the customer is not currently visited
            const Tour& tour = sol.tours[tourIdx];
            if (tour.customers.size() > 1) { // A tour must have at least two customers to have distinct neighbors
                auto it = std::find(tour.customers.begin(), tour.customers.end(), sourceCustomer);
                if (it != tour.customers.end()) {
                    int cInTourIdx = std::distance(tour.customers.begin(), it);
                    int prevC = tour.customers[(cInTourIdx + tour.customers.size() - 1) % tour.customers.size()];
                    int nextC = tour.customers[(cInTourIdx + 1) % tour.customers.size()];
                    currentNeighborsToConsider.push_back(prevC);
                    currentNeighborsToConsider.push_back(nextC);
                }
            }
        }
        
        // Shuffle the collected `currentNeighborsToConsider` to add another layer of stochasticity
        // to the order in which potential new customers are evaluated.
        static thread_local std::mt19937 gen_shuffle(std::random_device{}()); 
        std::shuffle(currentNeighborsToConsider.begin(), currentNeighborsToConsider.end(), gen_shuffle);

        // Iterate through the potential neighbors and try to add them to the `selectedCustomersSet`.
        for (int neighbor : currentNeighborsToConsider) {
            // Ensure the neighbor is a valid customer (index > 0 and within bounds)
            // and has not been selected yet.
            if (neighbor > 0 && neighbor <= sol.instance.numCustomers && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                // Stochastic acceptance: not every close neighbor is chosen, adding diversity.
                // A high probability (e.g., 95%) still favors "connected" choices.
                if (getRandomFractionFast() < 0.95f) {
                    selectedCustomersSet.insert(neighbor);
                    selectedCustomersList.push_back(neighbor);
                    expansionCandidates.push_back(neighbor); // Add to candidates for further expansion
                    if (selectedCustomersList.size() == numCustomersToRemove) {
                        break; // Stop if target size is reached
                    }
                }
            }
        }
    }

    return selectedCustomersList;
}

// New heuristic for ordering the removed customers before greedy reinsertion.
// This function sorts the customers based on a stochastically chosen combination
// of criteria, aiming to guide the greedy reinsertion process effectively.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Use a thread-local random number generator for `std::shuffle` and other
    // stochastic choices to ensure thread-safety and good random distribution
    // over many iterations.
    static thread_local std::mt19937 gen(std::random_device{}());

    // Define different sorting criteria that can be combined.
    enum SortType {
        PRIZE_DESC,        // Prioritize customers with higher prizes
        DEMAND_ASC,        // Prioritize customers with lower demand (potentially easier to fit)
        DIST_DEPOT_ASC,    // Prioritize customers closer to the depot
        DEGREE_DESC,       // Prioritize customers with more geographical neighbors (potentially more flexible insertion points)
        RANDOM_FACTOR      // A purely random component to add diversity
    };

    // Stochastically choose 1 or 2 primary sorting criteria to combine.
    std::vector<SortType> chosenCriteria;
    std::uniform_int_distribution<> distSortType(0, 4); // Corresponds to PRIZE_DESC to RANDOM_FACTOR

    int numCriteria = getRandomNumber(1, 2); // Randomly choose to combine 1 or 2 criteria
    for (int i = 0; i < numCriteria; ++i) {
        chosenCriteria.push_back(static_cast<SortType>(distSortType(gen)));
    }

    // Sort the customers using a lambda function that calculates a combined score
    // for each customer based on the chosen criteria.
    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        float score1 = 0.0f;
        float score2 = 0.0f;

        // Calculate a combined score for each customer based on the selected criteria.
        // Positive contributions generally mean "higher priority" for descending sort.
        for (SortType type : chosenCriteria) {
            switch (type) {
                case PRIZE_DESC:
                    score1 += instance.prizes[c1];
                    score2 += instance.prizes[c2];
                    break;
                case DEMAND_ASC: // Lower demand is better for insertion, so add negative demand
                    score1 += -static_cast<float>(instance.demand[c1]);
                    score2 += -static_cast<float>(instance.demand[c2]);
                    break;
                case DIST_DEPOT_ASC: // Closer to depot is often preferred, so add negative distance
                    score1 += -instance.distanceMatrix[0][c1];
                    score2 += -instance.distanceMatrix[0][c2];
                    break;
                case DEGREE_DESC: // Higher degree (more neighbors) means more potential connections
                    score1 += static_cast<float>(instance.adj[c1].size());
                    score2 += static_cast<float>(instance.adj[c2].size());
                    break;
                case RANDOM_FACTOR: // Add a significant random component for overall diversity
                    score1 += getRandomFractionFast() * 100.0f; 
                    score2 += getRandomFractionFast() * 100.0f;
                    break;
            }
        }
        
        // Add a very small random tie-breaker. This is crucial for ensuring full stochasticity
        // and avoiding identical orders when combined scores are exactly the same, which helps
        // explore a wider search space over millions of iterations.
        score1 += getRandomFractionFast() * 0.001f; 
        score2 += getRandomFractionFast() * 0.001f;

        // Sort in descending order (highest score first).
        return score1 > score2;
    });
}