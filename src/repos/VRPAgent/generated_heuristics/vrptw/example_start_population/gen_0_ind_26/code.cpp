#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <numeric>
#include <cmath>
#include "Utils.h"

const int MIN_REMOVE_COUNT = 10;
const int MAX_REMOVE_COUNT = 25;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatePoolVector;
    std::unordered_set<int> candidatePoolSet;

    int numCustomersToRemove = getRandomNumber(MIN_REMOVE_COUNT, MAX_REMOVE_COUNT);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);

    for (int neighbor : sol.instance.adj[seedCustomer]) {
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            if (candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
                candidatePoolVector.push_back(neighbor);
                candidatePoolSet.insert(neighbor);
            }
        }
    }

    int tourIdx = sol.customerToTourMap[seedCustomer];
    if (tourIdx != -1 && tourIdx < sol.tours.size()) {
        for (int customerInTour : sol.tours[tourIdx].customers) {
            if (selectedCustomersSet.find(customerInTour) == selectedCustomersSet.end()) {
                if (candidatePoolSet.find(customerInTour) == candidatePoolSet.end()) {
                    candidatePoolVector.push_back(customerInTour);
                    candidatePoolSet.insert(customerInTour);
                }
            }
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatePoolVector.empty()) {
            std::vector<int> unselectedCustomers;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                    unselectedCustomers.push_back(i);
                }
            }
            if (unselectedCustomers.empty()) {
                break;
            }
            int newSeed = unselectedCustomers[getRandomNumber(0, unselectedCustomers.size() - 1)];
            selectedCustomersSet.insert(newSeed);

            for (int neighbor : sol.instance.adj[newSeed]) {
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    if (candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
                        candidatePoolVector.push_back(neighbor);
                        candidatePoolSet.insert(neighbor);
                    }
                }
            }
            int newSeedTourIdx = sol.customerToTourMap[newSeed];
            if (newSeedTourIdx != -1 && newSeedTourIdx < sol.tours.size()) {
                for (int customerInTour : sol.tours[newSeedTourIdx].customers) {
                    if (selectedCustomersSet.find(customerInTour) == selectedCustomersSet.end()) {
                        if (candidatePoolSet.find(customerInTour) == candidatePoolSet.end()) {
                            candidatePoolVector.push_back(customerInTour);
                            candidatePoolSet.insert(customerInTour);
                        }
                    }
                }
            }
            continue;
        }

        int idx = getRandomNumber(0, candidatePoolVector.size() - 1);
        int nextCustomer = candidatePoolVector[idx];

        candidatePoolVector[idx] = candidatePoolVector.back();
        candidatePoolVector.pop_back();
        candidatePoolSet.erase(nextCustomer);

        if (selectedCustomersSet.find(nextCustomer) != selectedCustomersSet.end()) {
            continue;
        }

        selectedCustomersSet.insert(nextCustomer);

        for (int neighbor : sol.instance.adj[nextCustomer]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (candidatePoolSet.find(neighbor) == candidatePoolSet.end()) {
                    candidatePoolVector.push_back(neighbor);
                    candidatePoolSet.insert(neighbor);
                }
            }
        }
        int nextCustomerTourIdx = sol.customerToTourMap[nextCustomer];
        if (nextCustomerTourIdx != -1 && nextCustomerTourIdx < sol.tours.size()) {
            for (int customerInTour : sol.tours[nextCustomerTourIdx].customers) {
                if (selectedCustomersSet.find(customerInTour) == selectedCustomersSet.end()) {
                    if (candidatePoolSet.find(customerInTour) == candidatePoolSet.end()) {
                        candidatePoolVector.push_back(customerInTour);
                        candidatePoolSet.insert(customerInTour);
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

    float max_tw_width = 0.0f;
    float max_service_time = 0.0f;
    float max_demand = 0.0f;
    float max_depot_dist = 0.0f;

    for (int customerId : customers) {
        max_tw_width = std::fmax(max_tw_width, instance.TW_Width[customerId]);
        max_service_time = std::fmax(max_service_time, instance.serviceTime[customerId]);
        max_demand = std::fmax(max_demand, static_cast<float>(instance.demand[customerId]));
        max_depot_dist = std::fmax(max_depot_dist, instance.distanceMatrix[0][customerId]);
    }

    const float EPSILON = 1e-6f;
    max_tw_width = std::fmax(max_tw_width, EPSILON);
    max_service_time = std::fmax(max_service_time, EPSILON);
    max_demand = std::fmax(max_demand, EPSILON);
    max_depot_dist = std::fmax(max_depot_dist, EPSILON);

    float w1 = getRandomFraction(0.0f, 1.0f);
    float w2 = getRandomFraction(0.0f, 1.0f);
    float w3 = getRandomFraction(0.0f, 1.0f);
    float w4 = getRandomFraction(0.0f, 1.0f);
    float sum_weights = w1 + w2 + w3 + w4;

    if (sum_weights < EPSILON) {
        w1 = w2 = w3 = w4 = 0.25f;
    } else {
        w1 /= sum_weights;
        w2 /= sum_weights;
        w3 /= sum_weights;
        w4 /= sum_weights;
    }

    for (int customerId : customers) {
        float normalized_tw_difficulty = (instance.TW_Width[customerId] > 0) ? (1.0f - (instance.TW_Width[customerId] / max_tw_width)) : 1.0f;
        float normalized_service_time = instance.serviceTime[customerId] / max_service_time;
        float normalized_demand = static_cast<float>(instance.demand[customerId]) / max_demand;
        float normalized_depot_dist = instance.distanceMatrix[0][customerId] / max_depot_dist;

        float composite_score = 
            w1 * normalized_tw_difficulty +
            w2 * normalized_service_time +
            w3 * normalized_demand +
            w4 * normalized_depot_dist;

        customerScores.push_back({composite_score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        if (std::abs(a.first - b.first) < 1e-5f) {
            return getRandomFraction() < 0.5f;
        }
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}