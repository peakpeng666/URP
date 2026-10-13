#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::min, std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"   // For getRandomNumber, getRandomFraction

// Define a thread-local random number generator for stochastic operations.
// This generator is used by std::shuffle and for certain stochastic decisions
// to ensure diversity across millions of iterations.
static thread_local std::mt19937 thread_local_gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidateQueue; // Stores customers to explore for removal
    std::unordered_set<int> candidateSet; // For fast checking if a customer is already in candidateQueue

    // Determine a stochastic number of customers to remove in this iteration.
    // This range is typically a small percentage of total customers for LNS.
    int numCustomersToRemove = getRandomNumber(10, 30);
    // Ensure not to try removing more customers than available in the instance.
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // Step 1: Select an initial seed customer to start the removal process.
    // Customer IDs are 1-indexed in the problem context (1 to numCustomers).
    // Array indices (e.g., for `instance.adj`, `prizes`, `demand`) are usually
    // 0-indexed for depot, 1 for customer 1, etc.
    // `customerToTourMap` is 0-indexed for customer 1 -> index 0.
    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeedCustomer);
    candidateQueue.push_back(initialSeedCustomer);
    candidateSet.insert(initialSeedCustomer);

    // Populate the initial candidate queue with neighbors of the seed customer.
    // This promotes the selection of geographically close customers.
    int numNeighborsToExplore = getRandomNumber(3, 8); // Stochastic number of neighbors to consider
    for (int neighborIdx = 0; neighborIdx < std::min((int)sol.instance.adj[initialSeedCustomer].size(), numNeighborsToExplore); ++neighborIdx) {
        int neighbor = sol.instance.adj[initialSeedCustomer][neighborIdx];
        if (neighbor == 0) continue; // Skip the depot (index 0)
        if (selectedCustomers.find(neighbor) == selectedCustomers.end()) { // If not already selected
            if (candidateSet.find(neighbor) == candidateSet.end()) { // If not already a candidate
                candidateQueue.push_back(neighbor);
                candidateSet.insert(neighbor);
            }
        }
    }

    // Also add customers from the same tour as the seed, if the seed customer is currently visited.
    // This promotes fragmenting existing tours.
    if (sol.customerToTourMap[initialSeedCustomer - 1] != -1) {
        const Tour& tour = sol.tours[sol.customerToTourMap[initialSeedCustomer - 1]];
        std::vector<int> tourCustomers = tour.customers;
        std::shuffle(tourCustomers.begin(), tourCustomers.end(), thread_local_gen); // Shuffle for stochastic selection

        int numTourMatesToAdd = getRandomNumber(1, std::min((int)tourCustomers.size(), 5)); // Add up to 5 random tour mates
        int addedCount = 0;
        for (int customer : tourCustomers) {
            if (customer == initialSeedCustomer) continue; // Skip the seed itself
            if (addedCount >= numTourMatesToAdd) break;

            if (selectedCustomers.find(customer) == selectedCustomers.end()) {
                if (candidateSet.find(customer) == candidateSet.end()) {
                    candidateQueue.push_back(customer);
                    candidateSet.insert(customer);
                    addedCount++;
                }
            }
        }
    }

    // Step 2: Iteratively select customers from the candidate queue until the target count is met.
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidateQueue.empty()) {
            // Fallback: If the candidate queue is exhausted (e.g., current "cluster" is too small),
            // pick a new random unselected customer as a new seed. This ensures we always reach `numCustomersToRemove`.
            int nextRandomCustomer = -1;
            while (true) { // Loop until a truly unselected customer is found
                nextRandomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(nextRandomCustomer) == selectedCustomers.end()) {
                    break;
                }
            }
            selectedCustomers.insert(nextRandomCustomer);
            candidateQueue.push_back(nextRandomCustomer);
            candidateSet.insert(nextRandomCustomer);

            // Re-populate candidates with neighbors and tour mates of this new seed
            numNeighborsToExplore = getRandomNumber(3, 8);
            for (int neighborIdx = 0; neighborIdx < std::min((int)sol.instance.adj[nextRandomCustomer].size(), numNeighborsToExplore); ++neighborIdx) {
                int neighbor = sol.instance.adj[nextRandomCustomer][neighborIdx];
                if (neighbor == 0) continue;
                if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    if (candidateSet.find(neighbor) == candidateSet.end()) {
                        candidateQueue.push_back(neighbor);
                        candidateSet.insert(neighbor);
                    }
                }
            }
            if (sol.customerToTourMap[nextRandomCustomer - 1] != -1) {
                const Tour& tour = sol.tours[sol.customerToTourMap[nextRandomCustomer - 1]];
                std::vector<int> tourCustomers = tour.customers;
                std::shuffle(tourCustomers.begin(), tourCustomers.end(), thread_local_gen);

                int numTourMatesToAdd = getRandomNumber(1, std::min((int)tourCustomers.size(), 3));
                int addedCount = 0;
                for (int customer : tourCustomers) {
                    if (customer == nextRandomCustomer) continue;
                    if (addedCount >= numTourMatesToAdd) break;

                    if (selectedCustomers.find(customer) == selectedCustomers.end()) {
                        if (candidateSet.find(customer) == candidateSet.end()) {
                            candidateQueue.push_back(customer);
                            candidateSet.insert(customer);
                            addedCount++;
                        }
                    }
                }
            }
            continue; // Continue to the next iteration to process the newly added candidates
        }

        // Select a customer from the candidate queue. A random index provides stochasticity
        // and helps explore different parts of the candidate set.
        int pickIndex = getRandomNumber(0, candidateQueue.size() - 1);
        int currentCustomer = candidateQueue[pickIndex];

        // Efficiently remove the selected customer from the candidate queue and set.
        std::swap(candidateQueue[pickIndex], candidateQueue.back());
        candidateQueue.pop_back();
        candidateSet.erase(currentCustomer);

        // If for some reason the customer was already selected (should be prevented by checks), skip.
        if (selectedCustomers.find(currentCustomer) != selectedCustomers.end()) {
            continue;
        }

        selectedCustomers.insert(currentCustomer);

        // Add the newly selected customer's neighbors to the candidate queue to expand the "removal area".
        numNeighborsToExplore = getRandomNumber(3, 8);
        for (int neighborIdx = 0; neighborIdx < std::min((int)sol.instance.adj[currentCustomer].size(), numNeighborsToExplore); ++neighborIdx) {
            int neighbor = sol.instance.adj[currentCustomer][neighborIdx];
            if (neighbor == 0) continue;
            if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                if (candidateSet.find(neighbor) == candidateSet.end()) {
                    candidateQueue.push_back(neighbor);
                    candidateSet.insert(neighbor);
                }
            }
        }

        // Also add other customers from the same tour to candidates, further encouraging tour fragmentation.
        if (sol.customerToTourMap[currentCustomer - 1] != -1) {
            const Tour& tour = sol.tours[sol.customerToTourMap[currentCustomer - 1]];
            std::vector<int> tourCustomers = tour.customers;
            std::shuffle(tourCustomers.begin(), tourCustomers.end(), thread_local_gen);

            int numTourMatesToAdd = getRandomNumber(1, std::min((int)tourCustomers.size(), 3));
            int addedCount = 0;
            for (int customer : tourCustomers) {
                if (customer == currentCustomer) continue;
                if (addedCount >= numTourMatesToAdd) break;

                if (selectedCustomers.find(customer) == selectedCustomers.end()) {
                    if (candidateSet.find(customer) == candidateSet.end()) {
                        candidateQueue.push_back(customer);
                        candidateSet.insert(customer);
                        addedCount++;
                    }
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<int, float>> customerScores;
    customerScores.reserve(customers.size());

    for (int customer : customers) {
        // Customer IDs are 1-indexed; array access for prizes and demand is 0-indexed.
        float prize = instance.prizes[customer - 1];
        float demand = instance.demand[customer - 1];

        // Calculate a score based on the prize-to-demand ratio.
        // This heuristic prioritizes customers that offer more profit per unit of demand,
        // making them potentially easier and more beneficial to reinsert into tours.
        // Adding 1.0f to demand prevents division by zero and smooths the ratio for very small demands.
        float score = prize / (demand + 1.0f);

        // Introduce stochasticity to the score. This small random perturbation ensures
        // that the sorting order varies slightly across iterations, even for customers
        // with identical base scores, promoting greater search diversity.
        score *= (1.0f + getRandomFraction(-0.05f, 0.05f)); // Perturb score by +/- 5%

        customerScores.push_back({customer, score});
    }

    // Sort customers in descending order based on their calculated score.
    // Customers with higher scores (more profitable/easier to place) will be reinserted first.
    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<int, float>& a, const std::pair<int, float>& b) {
        return a.second > b.second; // Sort by score in descending order
    });

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].first;
    }
}