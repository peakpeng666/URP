#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort
#include <vector> // For std::vector
#include <utility> // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> currentSelectionVector;

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int numCustomersToRemove = getRandomNumber(15, 30);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialCustomer);
    currentSelectionVector.push_back(initialCustomer);

    static thread_local std::mt19937 gen(std::random_device{}());

    while (selectedCustomers.size() < numCustomersToRemove) {
        bool addedNewCustomer = false;

        std::shuffle(currentSelectionVector.begin(), currentSelectionVector.end(), gen);

        for (int anchorCustomer : currentSelectionVector) {
            const auto& neighbors = sol.instance.adj[anchorCustomer];
            if (neighbors.empty()) continue;

            std::vector<int> potentialNeighbors;
            for (int neighbor : neighbors) {
                 if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    potentialNeighbors.push_back(neighbor);
                 }
            }

            if (!potentialNeighbors.empty()) {
                int chosenNeighbor = potentialNeighbors[getRandomNumber(0, potentialNeighbors.size() - 1)];

                selectedCustomers.insert(chosenNeighbor);
                currentSelectionVector.push_back(chosenNeighbor);
                addedNewCustomer = true;
                break;
            }
        }

        if (!addedNewCustomer) {
            int randomAttempts = 0;
            const int MAX_RANDOM_ATTEMPTS = 100;
            while (randomAttempts < MAX_RANDOM_ATTEMPTS) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
                    selectedCustomers.insert(randomCustomer);
                    currentSelectionVector.push_back(randomCustomer);
                    addedNewCustomer = true;
                    break;
                }
                randomAttempts++;
            }
            if (!addedNewCustomer) {
                break;
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());

    int strategy = getRandomNumber(0, 4);

    if (strategy == 4) {
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> sort_data;
    sort_data.reserve(customers.size());

    for (int customer : customers) {
        float value;
        switch (strategy) {
            case 0:
                value = instance.TW_Width[customer];
                break;
            case 1:
                value = -static_cast<float>(instance.demand[customer]);
                break;
            case 2:
                value = -instance.serviceTime[customer];
                break;
            case 3:
                value = -instance.distanceMatrix[0][customer];
                break;
            default:
                value = getRandomFraction();
                break;
        }
        sort_data.push_back({value, customer});
    }

    std::sort(sort_data.begin(), sort_data.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data[i].second;
    }
}