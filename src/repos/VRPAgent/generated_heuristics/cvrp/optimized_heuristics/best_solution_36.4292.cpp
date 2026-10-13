#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 15;
    const int MAX_CUSTOMERS_TO_REMOVE = 30;
    const int MAX_NEIGHBOR_EXPANSION_ATTEMPTS = 5;
    const int NEIGHBOR_BIAS_RANGE = 20;
    const float PROB_ADD_PROXIMITY_NEIGHBOR = 0.6f;
    const float PROB_CONSIDER_TOUR_NEIGHBOR = 0.25f;

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesForExpansion;

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    std::vector<int> customer_to_tour_map(sol.instance.numCustomers + 1, -1);
    for (int t_idx = 0; t_idx < sol.tours.size(); ++t_idx) {
        for (int customer_id_in_tour : sol.tours[t_idx].customers) {
            customer_to_tour_map[customer_id_in_tour] = t_idx;
        }
    }

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    } else if (numCustomersToRemove == 0) {
        return {};
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    candidatesForExpansion.push_back(seedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesForExpansion.empty()) {
            int newSeed;
            bool foundNewSeed = false;
            for (int attempt = 0; attempt < 50 && !foundNewSeed; ++attempt) {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(newSeed) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(newSeed);
                    candidatesForExpansion.push_back(newSeed);
                    foundNewSeed = true;
                }
            }
            if (!foundNewSeed) {
                break;
            }
            if (selectedCustomersSet.size() >= numCustomersToRemove) break;
            continue;
        }

        int currentCandidateIdx = getRandomNumber(0, candidatesForExpansion.size() - 1);
        int currentCustomer = candidatesForExpansion[currentCandidateIdx];

        if (getRandomFractionFast() < PROB_CONSIDER_TOUR_NEIGHBOR) {
            int currentCustomerTourIdx = customer_to_tour_map[currentCustomer];
            if (currentCustomerTourIdx != -1 && currentCustomerTourIdx < sol.tours.size()) {
                const auto& currentTourCustomers = sol.tours[currentCustomerTourIdx].customers;
                if (!currentTourCustomers.empty()) {
                    for (int tourAttempt = 0; tourAttempt < 3; ++tourAttempt) {
                        int chosenTourNeighborIdx = getRandomNumber(0, currentTourCustomers.size() - 1);
                        int chosenTourNeighbor = currentTourCustomers[chosenTourNeighborIdx];
                        if (chosenTourNeighbor != 0 && selectedCustomersSet.find(chosenTourNeighbor) == selectedCustomersSet.end()) {
                            selectedCustomersSet.insert(chosenTourNeighbor);
                            candidatesForExpansion.push_back(chosenTourNeighbor);
                            if (selectedCustomersSet.size() >= numCustomersToRemove) break;
                        }
                    }
                }
            }
        }
        if (selectedCustomersSet.size() >= numCustomersToRemove) break;

        const std::vector<int>& neighbors = sol.instance.adj[currentCustomer];
        int numNeighborsAvailable = neighbors.size();

        for (int attempt = 0; attempt < MAX_NEIGHBOR_EXPANSION_ATTEMPTS; ++attempt) {
            if (selectedCustomersSet.size() >= numCustomersToRemove) break;
            if (numNeighborsAvailable == 0) break;

            int effectiveMaxIdx = std::min(numNeighborsAvailable - 1, NEIGHBOR_BIAS_RANGE - 1);
            if (effectiveMaxIdx < 0) continue;

            int neighborIdx = static_cast<int>(getRandomFractionFast() * getRandomFractionFast() * (effectiveMaxIdx + 1));
            neighborIdx = std::min(neighborIdx, effectiveMaxIdx);
            neighborIdx = std::max(neighborIdx, 0);

            int neighbor = neighbors[neighborIdx];

            if (neighbor != 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (getRandomFractionFast() < PROB_ADD_PROXIMITY_NEIGHBOR) {
                    selectedCustomersSet.insert(neighbor);
                    candidatesForExpansion.push_back(neighbor);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    int pivotNodeId;
    if (getRandomFractionFast() < 0.7f) {
        pivotNodeId = customers[getRandomNumber(0, customers.size() - 1)];
    } else {
        pivotNodeId = 0;
    }

    std::vector<std::pair<float, int>> customerDistances;
    customerDistances.reserve(customers.size());

    const float SMALL_NOISE_MAGNITUDE = 0.001f;

    for (int customerId : customers) {
        float dist = instance.distanceMatrix[customerId][pivotNodeId];
        dist += getRandomFractionFast() * SMALL_NOISE_MAGNITUDE;
        customerDistances.emplace_back(dist, customerId);
    }

    std::sort(customerDistances.begin(), customerDistances.end());

    if (getRandomFractionFast() < 0.5f) {
        std::reverse(customerDistances.begin(), customerDistances.end());
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerDistances[i].second;
    }

    int numSwaps = getRandomNumber(1, std::min(5, (int)customers.size() / 2));
    if (customers.size() <= 2 && numSwaps > 0) numSwaps = 1;

    for (int i = 0; i < numSwaps; ++i) {
        int idx1 = getRandomNumber(0, customers.size() - 1);
        int idx2 = getRandomNumber(0, customers.size() - 1);
        if (idx1 != idx2) {
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}