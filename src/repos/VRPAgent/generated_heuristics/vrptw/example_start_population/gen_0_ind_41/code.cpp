#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <iterator>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> tourCustomers; 

    int numCustomersToRemove = getRandomNumber(15, 30);
    if (sol.instance.numCustomers == 0) return {};
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    
    int initialCustomer = -1;
    bool foundInitialCustomer = false;

    if (!sol.tours.empty()) {
        int maxTourAttempts = 10; 
        for (int i = 0; i < maxTourAttempts; ++i) {
            int randomTourIdx = getRandomNumber(0, static_cast<int>(sol.tours.size()) - 1);
            if (!sol.tours[randomTourIdx].customers.empty()) {
                tourCustomers = sol.tours[randomTourIdx].customers;
                initialCustomer = tourCustomers[getRandomNumber(0, static_cast<int>(tourCustomers.size()) - 1)];
                foundInitialCustomer = true;
                break;
            }
        }
    }

    if (!foundInitialCustomer) {
        initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    selectedCustomers.insert(initialCustomer);
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) numCustomersToRemove = 1;


    while (selectedCustomers.size() < numCustomersToRemove) {
        int customerAdded = -1;

        if (getRandomFraction() < 0.7 && !tourCustomers.empty()) {
            std::vector<int> unselectedTourCustomers;
            for (int cust : tourCustomers) {
                if (selectedCustomers.find(cust) == selectedCustomers.end()) {
                    unselectedTourCustomers.push_back(cust);
                }
            }
            if (!unselectedTourCustomers.empty()) {
                customerAdded = unselectedTourCustomers[getRandomNumber(0, static_cast<int>(unselectedTourCustomers.size()) - 1)];
            }
        }

        if (customerAdded == -1 && !selectedCustomers.empty()) {
            int pivotCustomerIdx = getRandomNumber(0, static_cast<int>(selectedCustomers.size()) - 1);
            auto it = selectedCustomers.begin();
            std::advance(it, pivotCustomerIdx);
            int pivotCustomer = *it;

            const auto& neighbors = sol.instance.adj[pivotCustomer]; 

            std::vector<int> unselectedNeighbors;
            for (int neighborNodeIdx : neighbors) {
                if (neighborNodeIdx > 0 && neighborNodeIdx <= sol.instance.numCustomers &&
                    selectedCustomers.find(neighborNodeIdx) == selectedCustomers.end()) {
                    unselectedNeighbors.push_back(neighborNodeIdx);
                }
            }

            if (!unselectedNeighbors.empty()) {
                customerAdded = unselectedNeighbors[getRandomNumber(0, static_cast<int>(unselectedNeighbors.size()) - 1)];
            }
        }

        if (customerAdded == -1) {
            int randomCustomer = -1;
            int attempts = 0;
            while (attempts < sol.instance.numCustomers * 2) {
                randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
                    break;
                }
                randomCustomer = -1; 
                attempts++;
            }
            if (randomCustomer != -1) {
                customerAdded = randomCustomer;
            } else {
                break;
            }
        }
        
        if (customerAdded != -1) {
            selectedCustomers.insert(customerAdded);
        } else {
            break;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float r = getRandomFraction();
    if (r < 0.7) { 
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.TW_Width[a] < instance.TW_Width[b];
        });
    } else if (r < 0.9) { 
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.TW_Width[a] > instance.TW_Width[b];
        });
    } else { 
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}