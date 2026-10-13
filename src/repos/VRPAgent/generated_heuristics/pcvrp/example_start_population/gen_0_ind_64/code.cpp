#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

// Constants for select_by_llm_1 (Customer Selection)
const int MIN_CUSTOMERS_TO_REMOVE = 15;
const int MAX_CUSTOMERS_TO_REMOVE = 35;
const int MAX_NEIGHBORS_TO_CONSIDER_FOR_EXPANSION = 10;
const float PROB_ADD_NEIGHBOR_TO_CLUSTER = 0.95f;
const float PROB_RANDOM_JUMP_IN_SELECTION = 0.10f;

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidateExpansionSources;

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);
    candidateExpansionSources.push_back(seedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidateExpansionSources.empty() || getRandomFractionFast() < PROB_RANDOM_JUMP_IN_SELECTION) {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
                selectedCustomers.insert(randomCustomer);
                candidateExpansionSources.push_back(randomCustomer);
                if (selectedCustomers.size() == numCustomersToRemove) {
                    break;
                }
            }
            if (selectedCustomers.size() >= numCustomersToRemove) break;
            if (candidateExpansionSources.empty()) continue;
        }

        int sourceNodeIdx = getRandomNumber(0, static_cast<int>(candidateExpansionSources.size()) - 1);
        int sourceNode = candidateExpansionSources[sourceNodeIdx];

        const auto& neighbors = sol.instance.adj[sourceNode];

        int neighborsConsidered = 0;
        for (int neighbor : neighbors) {
            if (neighborsConsidered >= MAX_NEIGHBORS_TO_CONSIDER_FOR_EXPANSION) {
                break;
            }
            neighborsConsidered++;

            if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                if (getRandomFractionFast() < PROB_ADD_NEIGHBOR_TO_CLUSTER) {
                    selectedCustomers.insert(neighbor);
                    candidateExpansionSources.push_back(neighbor);
                    if (selectedCustomers.size() == numCustomersToRemove) {
                        break;
                    }
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

static thread_local std::mt19937 sort_gen(std::random_device{}());

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.size() <= 1) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerId : customers) {
        float prize = instance.prizes[customerId];
        float distToDepot = instance.distanceMatrix[0][customerId];

        float baseCostEstimate = distToDepot;
        if (baseCostEstimate < 1e-6f) {
            baseCostEstimate = 1.0f;
        }
        float baseScore = prize / baseCostEstimate;

        float noisyScore = baseScore * (1.0f + getRandomFraction(-0.1f, 0.1f));
        
        customerScores.push_back({noisyScore, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}