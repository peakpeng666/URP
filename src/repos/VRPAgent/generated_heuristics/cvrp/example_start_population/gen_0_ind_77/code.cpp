#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    int numCustomers = sol.instance.numCustomers;
    int numToRemove = getRandomNumber(15, 30); 

    if (numToRemove <= 0) {
        return {};
    }

    selectedCustomersSet.insert(getRandomNumber(1, numCustomers));

    while (selectedCustomersSet.size() < numToRemove) {
        int customerToAdd = -1;

        if (!selectedCustomersSet.empty() && getRandomFractionFast() < 0.8) {
            auto it = selectedCustomersSet.begin();
            std::advance(it, getRandomNumber(0, selectedCustomersSet.size() - 1));
            int anchorCustomer = *it;

            const auto& neighbors = sol.instance.adj[anchorCustomer];
            int max_neighbors_to_check = std::min((int)neighbors.size(), 10); 

            std::vector<int> potential_neighbors;
            for(int i = 0; i < max_neighbors_to_check; ++i) {
                int neighbor_idx = neighbors[i];
                if (neighbor_idx != 0 && selectedCustomersSet.find(neighbor_idx) == selectedCustomersSet.end()) {
                    potential_neighbors.push_back(neighbor_idx);
                }
            }

            if (!potential_neighbors.empty()) {
                customerToAdd = potential_neighbors[getRandomNumber(0, potential_neighbors.size() - 1)];
            }
        }

        if (customerToAdd == -1) {
            customerToAdd = getRandomNumber(1, numCustomers);
            int safety_counter = 0;
            while (selectedCustomersSet.find(customerToAdd) != selectedCustomersSet.end() && safety_counter < numCustomers * 2) {
                customerToAdd = getRandomNumber(1, numCustomers);
                safety_counter++;
            }
            if (safety_counter >= numCustomers * 2) {
                break; 
            }
        }
        selectedCustomersSet.insert(customerToAdd);
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::sort(customers.begin(), customers.end(), [&](int c1_idx, int c2_idx) {
        int demand1 = instance.demand[c1_idx];
        int demand2 = instance.demand[c2_idx];

        if (demand1 != demand2) {
            return demand1 > demand2; 
        }

        float dist1_to_depot = instance.distanceMatrix[0][c1_idx];
        float dist2_to_depot = instance.distanceMatrix[0][c2_idx];
        return dist1_to_depot < dist2_to_depot;
    });

    int num_swaps = getRandomNumber(0, static_cast<int>(customers.size() * 0.2)); 
    for (int i = 0; i < num_swaps; ++i) {
        if (customers.size() < 2) break;
        int idx1 = getRandomNumber(0, customers.size() - 1);
        int idx2 = getRandomNumber(0, customers.size() - 1);
        std::swap(customers[idx1], customers[idx2]);
    }
}