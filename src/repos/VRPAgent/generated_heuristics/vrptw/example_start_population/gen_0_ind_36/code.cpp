#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentClusterCustomers;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int firstCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(firstCustomer);
    currentClusterCustomers.push_back(firstCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int pivotCustomerIndex = getRandomNumber(0, static_cast<int>(currentClusterCustomers.size()) - 1);
        int pivotCustomer = currentClusterCustomers[pivotCustomerIndex];

        std::vector<int> potentialNeighbors;
        for (int neighbor : sol.instance.adj[pivotCustomer]) {
            if (neighbor != 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                potentialNeighbors.push_back(neighbor);
            }
        }

        if (!potentialNeighbors.empty()) {
            int newCustomerIndex = getRandomNumber(0, static_cast<int>(potentialNeighbors.size()) - 1);
            int newCustomer = potentialNeighbors[newCustomerIndex];
            selectedCustomersSet.insert(newCustomer);
            currentClusterCustomers.push_back(newCustomer);
        } else {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            int attempts = 0;
            const int maxAttempts = 100;
            while (selectedCustomersSet.find(randomCustomer) != selectedCustomersSet.end() && attempts < maxAttempts) {
                randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
                selectedCustomersSet.insert(randomCustomer);
                currentClusterCustomers.push_back(randomCustomer);
            } else {
                break;
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.TW_Width[customer_id] + getRandomFractionFast() * 5.0f;
        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}