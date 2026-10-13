#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::min, std::shuffle
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeedCustomer);

    std::vector<int> candidateExpansionSources;
    candidateExpansionSources.push_back(initialSeedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove && !candidateExpansionSources.empty()) {
        int idxToExpandFrom = getRandomNumber(0, candidateExpansionSources.size() - 1);
        int currentCustomer = candidateExpansionSources[idxToExpandFrom];

        bool expanded = false;
        int numNeighborsToConsider = std::min((int)sol.instance.adj[currentCustomer].size(), getRandomNumber(1, 5));

        std::vector<int> potentialNewCustomers;
        for (int i = 0; i < numNeighborsToConsider; ++i) {
            int neighbor = sol.instance.adj[currentCustomer][i];
            if (neighbor > 0 && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                potentialNewCustomers.push_back(neighbor);
            }
        }

        if (!potentialNewCustomers.empty()) {
            int newCustomer = potentialNewCustomers[getRandomNumber(0, potentialNewCustomers.size() - 1)];
            selectedCustomers.insert(newCustomer);
            candidateExpansionSources.push_back(newCustomer);
            expanded = true;
        } else {
            candidateExpansionSources.erase(candidateExpansionSources.begin() + idxToExpandFrom);
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomers.insert(randomCustomer);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    float instance_max_tw_width = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        if (instance.TW_Width[i] > instance_max_tw_width) {
            instance_max_tw_width = instance.TW_Width[i];
        }
    }

    float random_scale = 0.01f * instance_max_tw_width;
    if (random_scale < 0.1f) random_scale = 0.1f;

    std::vector<float> scores(customers.size());
    for (size_t i = 0; i < customers.size(); ++i) {
        int customer_id = customers[i];
        scores[i] = instance.endTW[customer_id] + instance.TW_Width[customer_id] + getRandomFractionFast() * random_scale;
    }

    std::vector<int> p = argsort(scores);

    std::vector<int> sorted_customers(customers.size());
    for (size_t i = 0; i < customers.size(); ++i) {
        sorted_customers[i] = customers[p[i]];
    }
    customers = sorted_customers;
}