#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    int numCustomersToRemove = getRandomNumber(15, 30);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        std::vector<int> currentSelectedCustomers(selectedCustomersSet.begin(), selectedCustomersSet.end());
        
        if (currentSelectedCustomers.empty()) {
            break;
        }

        int anchorCustomerIndex = getRandomNumber(0, currentSelectedCustomers.size() - 1);
        int anchorCustomer = currentSelectedCustomers[anchorCustomerIndex];

        const std::vector<int>& neighbors = sol.instance.adj[anchorCustomer];
        
        std::vector<int> candidateNeighbors;
        int maxNeighborsToCheck = std::min((int)neighbors.size(), 20);

        for (int i = 0; i < maxNeighborsToCheck; ++i) {
            int neighbor = neighbors[i];
            if (neighbor > 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                candidateNeighbors.push_back(neighbor);
            }
        }

        if (candidateNeighbors.empty()) {
            int fallbackCustomer = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            while (selectedCustomersSet.find(fallbackCustomer) != selectedCustomersSet.end() && attempts < 100) {
                fallbackCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (selectedCustomersSet.find(fallbackCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(fallbackCustomer);
            } else {
                break;
            }
        } else {
            int selectedNeighborIndex = getRandomNumber(0, candidateNeighbors.size() - 1);
            selectedCustomersSet.insert(candidateNeighbors[selectedNeighborIndex]);
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_data;
    customer_data.reserve(customers.size());

    for (int customer_id : customers) {
        float jitter = getRandomFraction(0.0f, 0.01f) * instance.TW_Width[customer_id];
        customer_data.push_back({instance.TW_Width[customer_id] + jitter, customer_id});
    }

    std::sort(customer_data.begin(), customer_data.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first < b.first;
    });

    for (size_t i = 0; i < customer_data.size(); ++i) {
        customers[i] = customer_data[i].second;
    }
}