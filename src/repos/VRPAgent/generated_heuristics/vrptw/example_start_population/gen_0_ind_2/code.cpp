#include "AgentDesigned.h"
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <limits>

#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 25;
const int INITIAL_CLUSTER_SIZE_MAX = 5;
const int NEIGHBORS_TO_CONSIDER_PER_EXPANSION = 5;

const float ALPHA_SORT_BY_LLM = 0.4;
const float BETA_SORT_BY_LLM = 0.3;
const float GAMMA_SORT_BY_LLM = 0.3;
const float EPSILON_SORT_BY_LLM = 1e-6;
const int NUM_CLOSEST_REMOVED_TO_CONSIDER = 3;


std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> expansionCandidates;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);
    expansionCandidates.push_back(seedCustomer);

    int customersAdded = 1;
    for (int neighborId : sol.instance.adj[seedCustomer]) {
        if (customersAdded >= INITIAL_CLUSTER_SIZE_MAX || customersAdded >= numCustomersToRemove) {
            break;
        }
        if (selectedCustomers.count(neighborId) == 0) {
            selectedCustomers.insert(neighborId);
            expansionCandidates.push_back(neighborId);
            customersAdded++;
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (expansionCandidates.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.count(newSeed) > 0) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(newSeed);
            expansionCandidates.push_back(newSeed);
            customersAdded++;
        }

        int idx = getRandomNumber(0, expansionCandidates.size() - 1);
        int currentExpansionCustomer = expansionCandidates[idx];
        
        expansionCandidates[idx] = expansionCandidates.back();
        expansionCandidates.pop_back();

        int neighborsConsidered = 0;
        for (int neighborId : sol.instance.adj[currentExpansionCustomer]) {
            if (neighborsConsidered >= NEIGHBORS_TO_CONSIDER_PER_EXPANSION) break;
            
            if (selectedCustomers.count(neighborId) == 0) {
                selectedCustomers.insert(neighborId);
                expansionCandidates.push_back(neighborId);
                customersAdded++;
                if (selectedCustomers.size() >= numCustomersToRemove) break;
            }
            neighborsConsidered++;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    std::unordered_map<int, float> clusteringScores;
    for (int i = 0; i < customers.size(); ++i) {
        int c1 = customers[i];
        std::vector<float> distancesToOtherRemoved;
        distancesToOtherRemoved.reserve(customers.size() - 1);
        for (int j = 0; j < customers.size(); ++j) {
            if (i == j) continue;
            int c2 = customers[j];
            distancesToOtherRemoved.push_back(instance.distanceMatrix[c1][c2]);
        }

        float avgDist = 0.0;
        int numClosest = std::min((int)distancesToOtherRemoved.size(), NUM_CLOSEST_REMOVED_TO_CONSIDER);

        if (numClosest > 0) {
            std::nth_element(distancesToOtherRemoved.begin(), distancesToOtherRemoved.begin() + numClosest -1, distancesToOtherRemoved.end());
            for (int k = 0; k < numClosest; ++k) {
                avgDist += distancesToOtherRemoved[k];
            }
            avgDist /= numClosest;
        } else {
            avgDist = std::numeric_limits<float>::max();
        }
        
        clusteringScores[c1] = 1.0 / (avgDist + EPSILON_SORT_BY_LLM);
    }

    for (int customerId : customers) {
        float twScore = 1.0 / (instance.TW_Width[customerId] + EPSILON_SORT_BY_LLM);
        
        float demandScore = static_cast<float>(instance.demand[customerId]);

        float clstScore = clusteringScores[customerId];

        float combinedScore = ALPHA_SORT_BY_LLM * twScore +
                              BETA_SORT_BY_LLM * demandScore +
                              GAMMA_SORT_BY_LLM * clstScore;

        combinedScore += getRandomFractionFast() * 0.001; 

        scoredCustomers.push_back({combinedScore, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (int i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}