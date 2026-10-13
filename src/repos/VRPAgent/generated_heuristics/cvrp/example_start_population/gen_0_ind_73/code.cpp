#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;
const float PROXIMITY_SELECTION_PROB = 0.85f;
const int MAX_ADJ_TO_CONSIDER_FOR_SELECT = 10;
const int MAX_SELECT_TRIES_PROXIMITY = 50;
const int MAX_SELECT_TRIES_RANDOM = 50;

const float CONNECTIVITY_BONUS_WEIGHT = 0.5f;
const float STOCHASTIC_SORT_PERTURBATION = 0.01f;
const int MAX_ADJ_TO_CONSIDER_FOR_SORT_CONNECTIVITY = 10;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> customerCandidates;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int customerToAdd = -1;
        bool foundCustomer = false;

        if (selectedCustomers.empty() || getRandomFractionFast() < PROXIMITY_SELECTION_PROB) {
            int tries = 0;
            while (tries < MAX_SELECT_TRIES_PROXIMITY && !foundCustomer) {
                if (customerCandidates.empty()) break;

                int seedIdx = getRandomNumber(0, customerCandidates.size() - 1);
                int seedCustomer = customerCandidates[seedIdx];
                const auto& neighbors = sol.instance.adj[seedCustomer];

                if (neighbors.empty()) {
                    tries++;
                    continue;
                }

                int neighborIdxLimit = std::min((int)neighbors.size() - 1, MAX_ADJ_TO_CONSIDER_FOR_SELECT - 1);
                if (neighborIdxLimit < 0) {
                    tries++;
                    continue;
                }

                int potentialNeighborIdx = getRandomNumber(0, neighborIdxLimit);
                int potentialCustomer = neighbors[potentialNeighborIdx];

                if (potentialCustomer != 0 && selectedCustomers.find(potentialCustomer) == selectedCustomers.end()) {
                    customerToAdd = potentialCustomer;
                    foundCustomer = true;
                }
                tries++;
            }
        }

        if (!foundCustomer) {
            int tries = 0;
            while (tries < MAX_SELECT_TRIES_RANDOM && !foundCustomer) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
                    customerToAdd = randomCustomer;
                    foundCustomer = true;
                }
                tries++;
            }
        }

        if (foundCustomer) {
            selectedCustomers.insert(customerToAdd);
            customerCandidates.push_back(customerToAdd);
        } else {
            break;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    std::unordered_set<int> removedCustomersSet(customers.begin(), customers.end());

    for (int customerId : customers) {
        float score = static_cast<float>(instance.demand[customerId]);

        int connectivityCount = 0;
        const auto& neighbors = instance.adj[customerId];
        for (int i = 0; i < std::min((int)neighbors.size(), MAX_ADJ_TO_CONSIDER_FOR_SORT_CONNECTIVITY); ++i) {
            int neighbor = neighbors[i];
            if (neighbor != 0 && removedCustomersSet.count(neighbor)) {
                connectivityCount++;
            }
        }
        score += connectivityCount * CONNECTIVITY_BONUS_WEIGHT;
        score += getRandomFractionFast() * STOCHASTIC_SORT_PERTURBATION;

        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}