#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>

#include "Utils.h"

const float P_RANDOM_PICK_FROM_ALL = 0.15f; 
const int MAX_ADJ_NEIGHBORS_TO_CONSIDER = 20; 
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 30;
const float PERCENTAGE_MIN_REMOVE = 0.015f; 
const float PERCENTAGE_MAX_REMOVE = 0.035f; 

const float W_DEMAND = 2.0f;
const float W_AVG_DIST = 1.0f;
const float W_DIST_DEPOT = 0.5f;
const float RANDOM_PERTURBATION_MAGNITUDE = 0.05f; 

static thread_local std::mt19937 sort_gen(std::random_device{}());
static thread_local std::uniform_real_distribution<float> sort_dist(0.0f, 1.0f);


std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;

    int numCustomers = sol.instance.numCustomers;
    int numCustomersToRemove = getRandomNumber(
        std::max(MIN_CUSTOMERS_TO_REMOVE, static_cast<int>(numCustomers * PERCENTAGE_MIN_REMOVE)),
        std::min(MAX_CUSTOMERS_TO_REMOVE, static_cast<int>(numCustomers * PERCENTAGE_MAX_REMOVE))
    );

    if (numCustomersToRemove == 0) {
        return {};
    }

    if (numCustomersToRemove > numCustomers) {
        numCustomersToRemove = numCustomers;
    }

    int firstCustomerIdx = getRandomNumber(1, numCustomers);
    selectedCustomersSet.insert(firstCustomerIdx);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (getRandomFractionFast() < P_RANDOM_PICK_FROM_ALL) {
            int randomCustomer = getRandomNumber(1, numCustomers);
            int attempts = 0;
            while (selectedCustomersSet.count(randomCustomer) && attempts < numCustomers) {
                randomCustomer = getRandomNumber(1, numCustomers);
                attempts++;
            }
            if (!selectedCustomersSet.count(randomCustomer)) { 
                selectedCustomersSet.insert(randomCustomer);
            } else {
                for (int i = 1; i <= numCustomers; ++i) {
                    if (!selectedCustomersSet.count(i)) {
                        selectedCustomersSet.insert(i);
                        break;
                    }
                }
            }
        }
        else {
            int anchorCustomerIdx = 0;
            if (!selectedCustomersSet.empty()) {
                auto it = selectedCustomersSet.begin();
                std::advance(it, getRandomNumber(0, static_cast<int>(selectedCustomersSet.size() - 1)));
                anchorCustomerIdx = *it;
            } else {
                anchorCustomerIdx = getRandomNumber(1, numCustomers);
            }

            bool customerAdded = false;
            int neighborsConsidered = 0;
            for (int neighborIdx : sol.instance.adj[anchorCustomerIdx]) {
                if (neighborIdx == 0) continue; 
                if (selectedCustomersSet.count(neighborIdx) == 0) {
                    selectedCustomersSet.insert(neighborIdx);
                    customerAdded = true;
                    break; 
                }
                neighborsConsidered++;
                if (neighborsConsidered >= MAX_ADJ_NEIGHBORS_TO_CONSIDER) {
                    break;
                }
            }

            if (!customerAdded && selectedCustomersSet.size() < numCustomersToRemove) {
                int randomCustomer = getRandomNumber(1, numCustomers);
                int attempts = 0;
                while (selectedCustomersSet.count(randomCustomer) && attempts < numCustomers) {
                    randomCustomer = getRandomNumber(1, numCustomers);
                    attempts++;
                }
                if (!selectedCustomersSet.count(randomCustomer)) {
                    selectedCustomersSet.insert(randomCustomer);
                } else {
                     for (int i = 1; i <= numCustomers; ++i) {
                        if (!selectedCustomersSet.count(i)) {
                            selectedCustomersSet.insert(i);
                            break;
                        }
                    }
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

    for (int c_id : customers) {
        float avgDistToOthersInRemovedSet = 0.0f;
        int countForAvgDist = 0;

        if (customers.size() > 1) {
            for (int other_c_id : customers) {
                if (c_id != other_c_id) {
                    avgDistToOthersInRemovedSet += instance.distanceMatrix[c_id][other_c_id];
                    countForAvgDist++;
                }
            }
            if (countForAvgDist > 0) {
                avgDistToOthersInRemovedSet /= countForAvgDist;
            } else {
                avgDistToOthersInRemovedSet = 0.0f;
            }
        } else {
            avgDistToOthersInRemovedSet = 0.0f;
        }
        
        float demandVal = static_cast<float>(instance.demand[c_id]);
        float distToDepotVal = instance.distanceMatrix[0][c_id];

        float score = W_DEMAND * demandVal
                      - W_AVG_DIST * avgDistToOthersInRemovedSet
                      - W_DIST_DEPOT * distToDepotVal
                      + RANDOM_PERTURBATION_MAGNITUDE * (sort_dist(sort_gen) - 0.5f);

        customerScores.push_back({score, c_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}