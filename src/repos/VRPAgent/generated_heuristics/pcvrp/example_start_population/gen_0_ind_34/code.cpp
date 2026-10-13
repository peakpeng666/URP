#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include "Utils.h"
#include "Solution.h" 

const int NUM_CUSTOMERS_TO_REMOVE_MIN = 10;
const int NUM_CUSTOMERS_TO_REMOVE_MAX = 20;
const float EXPANSION_PROBABILITY = 0.7f;
const float FALLBACK_EXPANSION_PROBABILITY = 0.9f; 
const float SORT_NOISE_FACTOR = 0.001f;     

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> expansionCandidates;

    int numCustomersToRemove = getRandomNumber(NUM_CUSTOMERS_TO_REMOVE_MIN, NUM_CUSTOMERS_TO_REMOVE_MAX);

    int initialSeed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeed);
    expansionCandidates.push_back(initialSeed);

    int attempts = 0; 

    while (selectedCustomers.size() < numCustomersToRemove && attempts < 2 * numCustomersToRemove * sol.instance.numCustomers) {
        if (expansionCandidates.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.count(newSeed)) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(newSeed);
            expansionCandidates.push_back(newSeed);
            if (selectedCustomers.size() == numCustomersToRemove) break;
        }

        int expandFromIdx = getRandomNumber(0, expansionCandidates.size() - 1);
        int currentCustomer = expansionCandidates[expandFromIdx];

        bool addedNew = false;
        for (int neighbor : sol.instance.adj[currentCustomer]) {
            if (selectedCustomers.count(neighbor) == 0) {
                float currentProb = EXPANSION_PROBABILITY;
                if (expansionCandidates.size() < 2) { 
                    currentProb = FALLBACK_EXPANSION_PROBABILITY;
                }
                if (getRandomFractionFast() < currentProb) {
                    selectedCustomers.insert(neighbor);
                    expansionCandidates.push_back(neighbor);
                    addedNew = true;
                    break; 
                }
            }
        }

        if (!addedNew) {
            expansionCandidates.erase(expansionCandidates.begin() + expandFromIdx);
        }
        attempts++;
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomers.insert(randomCustomer); 
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float score = instance.prizes[customerId];
        score += getRandomFractionFast() * SORT_NOISE_FACTOR;
        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; 
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}