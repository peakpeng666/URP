#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle and std::sort
#include <vector>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(15, 30); 

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int pivotCustomer = -1;
        int randomIdx = getRandomNumber(0, static_cast<int>(selectedCustomers.size()) - 1);
        auto it = selectedCustomers.begin();
        std::advance(it, randomIdx);
        pivotCustomer = *it;

        bool addedNew = false;
        int neighbors_to_check = std::min(static_cast<int>(sol.instance.adj[pivotCustomer].size()), getRandomNumber(3, 8));

        for (int i = 0; i < neighbors_to_check; ++i) {
            int neighbor = sol.instance.adj[pivotCustomer][i];
            if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                selectedCustomers.insert(neighbor);
                addedNew = true;
                break;
            }
        }

        if (!addedNew && selectedCustomers.size() < numCustomersToRemove) {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            selectedCustomers.insert(randomCustomer);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Solution& sol) {
    static thread_local std::mt19937 gen(std::random_device{}());

    int strategy_choice = getRandomNumber(0, 3); 

    if (strategy_choice == 0) {
        std::shuffle(customers.begin(), customers.end(), gen);
    } else if (strategy_choice == 1) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            bool c1_was_visited = (sol.customerToTourMap[c1] != -1);
            bool c2_was_visited = (sol.customerToTourMap[c2] != -1);

            if (c1_was_visited != c2_was_visited) {
                return c1_was_visited > c2_was_visited;
            }

            float prize1 = sol.instance.prizes[c1];
            float prize2 = sol.instance.prizes[c2];
            if (prize1 != prize2) {
                return prize1 > prize2;
            }

            float dist1 = sol.instance.distanceMatrix[0][c1];
            float dist2 = sol.instance.distanceMatrix[0][c2];
            if (dist1 != dist2) {
                return dist1 < dist2;
            }

            return getRandomFractionFast() < 0.5;
        });
    } else if (strategy_choice == 2) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float prize1 = sol.instance.prizes[c1];
            float prize2 = sol.instance.prizes[c2];
            if (prize1 != prize2) {
                return prize1 > prize2;
            }

            int demand1 = sol.instance.demand[c1];
            int demand2 = sol.instance.demand[c2];
            if (demand1 != demand2) {
                return demand1 < demand2;
            }

            float dist1 = sol.instance.distanceMatrix[0][c1];
            float dist2 = sol.instance.distanceMatrix[0][c2];
            if (dist1 != dist2) {
                return dist1 < dist2;
            }

            return getRandomFractionFast() < 0.5;
        });
    } else { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float key1 = (sol.instance.prizes[c1] * 1000.0f - sol.instance.demand[c1] + sol.instance.distanceMatrix[0][c1]) * getRandomFraction(0.9f, 1.1f);
            float key2 = (sol.instance.prizes[c2] * 1000.0f - sol.instance.demand[c2] + sol.instance.distanceMatrix[0][c2]) * getRandomFraction(0.9f, 1.1f);
            
            return key1 < key2;
        });
    }
}