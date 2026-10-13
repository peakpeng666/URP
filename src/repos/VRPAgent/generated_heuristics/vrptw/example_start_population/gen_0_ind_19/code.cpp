#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::min, std::shuffle
#include <vector>    // For std::vector
#include <utility>   // For std::pair

// Assuming Utils.h provides these functions:
// int getRandomNumber(int min, int max);
// float getRandomFraction(float min = 0.0, float max = 1.0);
// float getRandomFractionFast(); // Function to generate a random fraction (float) in the range [0, 1] using a fast method

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    std::vector<int> allCustomers;
    allCustomers.reserve(sol.instance.numCustomers);
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        allCustomers.push_back(i);
    }
    
    int currentCustomerIdx = -1;

    // Initial Seed Customer Selection
    if (sol.tours.empty()) {
        currentCustomerIdx = allCustomers[getRandomNumber(0, allCustomers.size() - 1)];
    } else {
        int maxTourAttempts = 10;
        int tourAttempt = 0;
        int randTourIdx = getRandomNumber(0, sol.tours.size() - 1);
        while (sol.tours[randTourIdx].customers.empty() && tourAttempt < maxTourAttempts && sol.tours.size() > 1) {
            randTourIdx = getRandomNumber(0, sol.tours.size() - 1);
            tourAttempt++;
        }
        
        if (!sol.tours[randTourIdx].customers.empty()) {
            currentCustomerIdx = sol.tours[randTourIdx].customers[getRandomNumber(0, sol.tours[randTourIdx].customers.size() - 1)];
        } else {
            currentCustomerIdx = allCustomers[getRandomNumber(0, allCustomers.size() - 1)];
        }
    }

    if (currentCustomerIdx != -1) {
        selectedCustomersSet.insert(currentCustomerIdx);
    } else {
        return {};
    }

    // Expand from selected customers using adjacency list
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        bool expandedThisIteration = false;
        std::vector<int> currentSelectedVec(selectedCustomersSet.begin(), selectedCustomersSet.end());
        
        if (currentSelectedVec.empty()) { // Should not happen if currentCustomerIdx was inserted
            break; 
        }

        int expandFromCustomer = currentSelectedVec[getRandomNumber(0, currentSelectedVec.size() - 1)];

        const float PROB_ADD_NEIGHBOR = 0.7f; // Probability to add a neighbor

        for (int neighbor : sol.instance.adj[expandFromCustomer]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (getRandomFractionFast() < PROB_ADD_NEIGHBOR) {
                    selectedCustomersSet.insert(neighbor);
                    expandedThisIteration = true;
                    break;
                }
            }
        }

        if (!expandedThisIteration) {
            int randomSeedAttempts = 0;
            const int MAX_RANDOM_SEED_ATTEMPTS = 50; 
            while(selectedCustomersSet.size() < numCustomersToRemove && randomSeedAttempts < MAX_RANDOM_SEED_ATTEMPTS) {
                int newSeedIdx = getRandomNumber(0, allCustomers.size() - 1);
                int newSeedCustomer = allCustomers[newSeedIdx];
                if (selectedCustomersSet.find(newSeedCustomer) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(newSeedCustomer);
                    expandedThisIteration = true;
                    break;
                }
                randomSeedAttempts++;
            }
        }

        if (!expandedThisIteration && selectedCustomersSet.size() < numCustomersToRemove) {
            // Fallback: If still couldn't expand and not enough customers, just pick random
            // This should rarely be hit if MAX_RANDOM_SEED_ATTEMPTS is sufficiently large and numCustomersToRemove < numCustomers
            for (int cust : allCustomers) {
                if (selectedCustomersSet.find(cust) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(cust);
                    break; 
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    const float TW_WIDTH_WEIGHT = 5.0f;
    const float SERVICE_TIME_WEIGHT = 2.0f;
    const float DEMAND_WEIGHT = 1.0f;
    const float RANDOM_PERTURBATION_SCALE = 0.5f;

    for (int customer_id : customers) {
        float score = 0.0f;

        float tw_tightness_score = 0.0f;
        if (instance.TW_Width[customer_id] > 0.0f) {
            tw_tightness_score = 1.0f / instance.TW_Width[customer_id];
        } else {
            tw_tightness_score = 1000.0f; 
        }
        score += TW_WIDTH_WEIGHT * tw_tightness_score;

        score += SERVICE_TIME_WEIGHT * instance.serviceTime[customer_id];

        score += DEMAND_WEIGHT * instance.demand[customer_id];

        float perturbation_amount = getRandomFractionFast() * 2.0f - 1.0f;
        score += RANDOM_PERTURBATION_SCALE * perturbation_amount;

        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}