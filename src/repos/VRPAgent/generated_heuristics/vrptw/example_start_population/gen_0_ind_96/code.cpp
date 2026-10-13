#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility> // For std::pair
#include "Utils.h" // For getRandomNumber, getRandomFraction, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomers = sol.instance.numCustomers;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 30;
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, numCustomers);
    selectedCustomers.insert(initialCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int expandFromCustomer = *std::next(selectedCustomers.begin(), getRandomNumber(0, selectedCustomers.size() - 1));

        bool customerAdded = false;
        float probFromTour = 0.7f;
        if (getRandomFraction() < probFromTour) {
            int tourIdx = sol.customerToTourMap[expandFromCustomer];
            if (tourIdx != -1) {
                const Tour& tour = sol.tours[tourIdx];
                std::vector<int> tourCustomersCandidates;
                for (int c : tour.customers) {
                    if (selectedCustomers.find(c) == selectedCustomers.end()) {
                        tourCustomersCandidates.push_back(c);
                    }
                }
                if (!tourCustomersCandidates.empty()) {
                    int chosenCustomer = tourCustomersCandidates[getRandomNumber(0, tourCustomersCandidates.size() - 1)];
                    selectedCustomers.insert(chosenCustomer);
                    customerAdded = true;
                }
            }
        }

        if (!customerAdded) {
            const std::vector<int>& neighbors = sol.instance.adj[expandFromCustomer];
            std::vector<int> neighborCandidates;
            int maxNeighborsToConsider = std::min((int)neighbors.size(), 15);
            for (int i = 0; i < maxNeighborsToConsider; ++i) {
                if (selectedCustomers.find(neighbors[i]) == selectedCustomers.end()) {
                    neighborCandidates.push_back(neighbors[i]);
                }
            }
            if (!neighborCandidates.empty()) {
                int chosenCustomer = neighborCandidates[getRandomNumber(0, neighborCandidates.size() - 1)];
                selectedCustomers.insert(chosenCustomer);
                customerAdded = true;
            }
        }

        if (!customerAdded) {
            int randomCustomer = getRandomNumber(1, numCustomers);
            while (selectedCustomers.count(randomCustomer) || randomCustomer == 0) {
                randomCustomer = getRandomNumber(1, numCustomers);
            }
            selectedCustomers.insert(randomCustomer);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;

    float maxTWWidth = 0.0f;
    float maxServiceTime = 0.0f;
    int maxDemand = 0;
    for (int customerId = 1; customerId <= instance.numCustomers; ++customerId) {
        maxTWWidth = std::max(maxTWWidth, instance.TW_Width[customerId]);
        maxServiceTime = std::max(maxServiceTime, instance.serviceTime[customerId]);
        maxDemand = std::max(maxDemand, instance.demand[customerId]);
    }

    if (maxTWWidth == 0) maxTWWidth = 1.0f;
    if (maxServiceTime == 0) maxServiceTime = 1.0f;
    if (maxDemand == 0) maxDemand = 1;

    for (int customerId : customers) {
        float score = 0.0f;

        score += (1.0f - (instance.TW_Width[customerId] / maxTWWidth)) * 0.5f;

        score += (instance.serviceTime[customerId] / maxServiceTime) * 0.3f;

        score += ((float)instance.demand[customerId] / maxDemand) * 0.2f;

        float noise = getRandomFractionFast() * 0.1f;
        score += noise;

        scoredCustomers.push_back({score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}