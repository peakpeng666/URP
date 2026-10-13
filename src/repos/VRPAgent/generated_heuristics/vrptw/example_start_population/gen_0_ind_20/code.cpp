#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 30);

    if (sol.instance.numCustomers == 0) {
        return {};
    }
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);

    int attempts = 0;
    const int maxAttempts = numCustomersToRemove * 5;

    while (selectedCustomers.size() < numCustomersToRemove && attempts < maxAttempts) {
        attempts++;

        int sourceCustomerIdx = 0;
        int rand_offset = getRandomNumber(0, (int)selectedCustomers.size() - 1);
        auto it = selectedCustomers.begin();
        std::advance(it, rand_offset);
        sourceCustomerIdx = *it;

        bool pickedNewCustomer = false;

        if (getRandomFraction() < 0.6) {
            int currentTourIdx = sol.customerToTourMap[sourceCustomerIdx];
            if (currentTourIdx != -1 && currentTourIdx < sol.tours.size()) {
                const Tour& currentTour = sol.tours[currentTourIdx];
                if (!currentTour.customers.empty()) {
                    int rand_tour_offset = getRandomNumber(0, (int)currentTour.customers.size() - 1);
                    int candidateCustomer = currentTour.customers[rand_tour_offset];

                    if (selectedCustomers.find(candidateCustomer) == selectedCustomers.end()) {
                        selectedCustomers.insert(candidateCustomer);
                        pickedNewCustomer = true;
                    }
                }
            }
        }

        if (!pickedNewCustomer) {
            const auto& neighbors = sol.instance.adj[sourceCustomerIdx];
            if (!neighbors.empty()) {
                int numNeighborsToConsider = std::min((int)neighbors.size(), 10);
                std::vector<int> candidateNeighbors;
                for (int i = 0; i < numNeighborsToConsider; ++i) {
                    int potentialNeighborNode = neighbors[i];
                    if (potentialNeighborNode >= 1 && potentialNeighborNode <= sol.instance.numCustomers &&
                        selectedCustomers.find(potentialNeighborNode) == selectedCustomers.end()) {
                        candidateNeighbors.push_back(potentialNeighborNode);
                    }
                }

                if (!candidateNeighbors.empty()) {
                    int rand_neighbor_idx = getRandomNumber(0, (int)candidateNeighbors.size() - 1);
                    selectedCustomers.insert(candidateNeighbors[rand_neighbor_idx]);
                    pickedNewCustomer = true;
                }
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
            selectedCustomers.insert(randomCustomer);
        }
        if (attempts++ > sol.instance.numCustomers * 2) break;
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int choice = getRandomNumber(0, 3);
    bool ascending = getRandomFraction() < 0.5;

    if (choice == 0) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            if (ascending) {
                return instance.TW_Width[a] < instance.TW_Width[b];
            } else {
                return instance.TW_Width[a] > instance.TW_Width[b];
            }
        });
    } else if (choice == 1) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            if (ascending) {
                return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
            } else {
                return instance.distanceMatrix[0][a] > instance.distanceMatrix[0][b];
            }
        });
    } else if (choice == 2) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            if (ascending) {
                return instance.demand[a] < instance.demand[b];
            } else {
                return instance.demand[a] > instance.demand[b];
            }
        });
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}