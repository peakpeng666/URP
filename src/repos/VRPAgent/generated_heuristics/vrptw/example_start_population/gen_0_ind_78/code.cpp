#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

static thread_local std::mt19937 gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomersToRemove = getRandomNumber(15, 25);
    
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    } else if (numCustomersToRemove == 0) { // If no customers at all
        return {};
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersList.push_back(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int pivotIndex = getRandomNumber(0, (int)selectedCustomersList.size() - 1);
        int pivotCustomer = selectedCustomersList[pivotIndex];

        bool customerAddedInIteration = false;
        int numNeighborsToCheck = getRandomNumber(5, 15);

        for (int i = 0; i < numNeighborsToCheck && i < sol.instance.adj[pivotCustomer].size(); ++i) {
            int potentialCustomer = sol.instance.adj[pivotCustomer][i];

            if (potentialCustomer != 0 && selectedCustomersSet.find(potentialCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(potentialCustomer);
                selectedCustomersList.push_back(potentialCustomer);
                customerAddedInIteration = true;
                break;
            }
        }

        if (!customerAddedInIteration) {
            int randomUnselected = -1;
            int attempts = 0;
            const int maxAttempts = sol.instance.numCustomers * 2; 

            while (attempts < maxAttempts) {
                randomUnselected = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomersSet.find(randomUnselected) == selectedCustomersSet.end()) {
                    break;
                }
                attempts++;
            }
            if (randomUnselected != -1 && selectedCustomersSet.find(randomUnselected) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(randomUnselected);
                selectedCustomersList.push_back(randomUnselected);
            } else {
                break; 
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    if (getRandomFraction() < 0.15) {
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    int sortMethodChoice = getRandomNumber(0, 3);

    std::vector<std::pair<float, int>> customerValues;
    customerValues.reserve(customers.size());

    for (int customerId : customers) {
        float value;
        switch (sortMethodChoice) {
            case 0: 
                value = instance.TW_Width[customerId];
                break;
            case 1: 
                value = -static_cast<float>(instance.demand[customerId]);
                break;
            case 2: 
                value = -instance.distanceMatrix[0][customerId];
                break;
            case 3: 
                value = static_cast<float>(instance.adj[customerId].size());
                break;
            default: 
                value = instance.TW_Width[customerId];
                break;
        }
        value += (getRandomFractionFast() - 0.5f) * 0.001f; 
        customerValues.push_back({value, customerId});
    }

    std::sort(customerValues.begin(), customerValues.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerValues[i].second;
    }
}