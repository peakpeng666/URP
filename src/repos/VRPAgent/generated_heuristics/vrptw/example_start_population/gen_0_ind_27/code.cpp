#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomers = sol.instance.numCustomers;
    int numToRemove = getRandomNumber(static_cast<int>(numCustomers * 0.02), static_cast<int>(numCustomers * 0.05));
    numToRemove = std::max(5, std::min(numToRemove, 40));

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int initialCustomer = getRandomNumber(1, numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersList.push_back(initialCustomer);

    static thread_local std::mt19937 generator(std::random_device{}());

    while (selectedCustomersSet.size() < numToRemove) {
        int nextCustomer = -1;
        
        std::vector<int> shuffledSelectedList = selectedCustomersList;
        std::shuffle(shuffledSelectedList.begin(), shuffledSelectedList.end(), generator);

        for (int pivotCustomer : shuffledSelectedList) {
            for (int neighbor : sol.instance.adj[pivotCustomer]) {
                if (neighbor != 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    nextCustomer = neighbor;
                    goto found_neighbor;
                }
            }
        }

    found_neighbor:;

        if (nextCustomer != -1) {
            selectedCustomersSet.insert(nextCustomer);
            selectedCustomersList.push_back(nextCustomer);
        } else {
            int randomCustomer = getRandomNumber(1, numCustomers);
            int attempts = 0;
            while (selectedCustomersSet.find(randomCustomer) != selectedCustomersSet.end() && attempts < 100) {
                randomCustomer = getRandomNumber(1, numCustomers);
                attempts++;
            }
            if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(randomCustomer);
                selectedCustomersList.push_back(randomCustomer);
            } else {
                break;
            }
        }
    }
    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int criterion = getRandomNumber(0, 4);

    switch (criterion) {
        case 0:
            std::sort(customers.begin(), customers.end(), [&](int a, int b) {
                return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
            });
            break;
        case 1:
            std::sort(customers.begin(), customers.end(), [&](int a, int b) {
                return instance.startTW[a] < instance.startTW[b];
            });
            break;
        case 2:
            std::sort(customers.begin(), customers.end(), [&](int a, int b) {
                return instance.TW_Width[a] < instance.TW_Width[b];
            });
            break;
        case 3:
            std::sort(customers.begin(), customers.end(), [&](int a, int b) {
                return instance.demand[a] > instance.demand[b];
            });
            break;
        case 4:
            std::sort(customers.begin(), customers.end(), [&](int a, int b) {
                return instance.serviceTime[a] > instance.serviceTime[b];
            });
            break;
        default:
            static thread_local std::mt19937 gen(std::random_device{}());
            std::shuffle(customers.begin(), customers.end(), gen);
            break;
    }
}