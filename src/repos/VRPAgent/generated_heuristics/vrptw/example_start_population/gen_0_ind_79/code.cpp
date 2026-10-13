#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>
#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;

const int NUM_NEIGHBORS_TO_EXPLORE_FOR_CLUSTER_EXPANSION = 50;

const int NUM_CLUSTER_CANDIDATES_TO_SAMPLE_FROM = 100;

const float CLUSTER_SELECTION_PULL_STRENGTH = 3.0f;

const int NUM_SORT_CANDIDATES_TO_SAMPLE_FROM = 5;

const float SORT_SELECTION_PULL_STRENGTH = 2.0f;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList; 

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (sol.instance.numCustomers == 0 || numCustomersToRemove == 0) {
        return {};
    }

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersList.push_back(seedCustomer);

    std::vector<std::pair<float, int>> potentialCandidates;

    while (selectedCustomersList.size() < numCustomersToRemove) {
        potentialCandidates.clear();

        for (int c_in_cluster : selectedCustomersList) {
            for (size_t i = 0; i < std::min((size_t)NUM_NEIGHBORS_TO_EXPLORE_FOR_CLUSTER_EXPANSION, sol.instance.adj[c_in_cluster].size()); ++i) {
                int neighbor_id = sol.instance.adj[c_in_cluster][i];
                if (neighbor_id != 0 && selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                    potentialCandidates.push_back({sol.instance.distanceMatrix[c_in_cluster][neighbor_id], neighbor_id});
                }
            }
        }

        if (potentialCandidates.empty()) {
            break;
        }

        std::sort(potentialCandidates.begin(), potentialCandidates.end());

        int numCandidatesToConsider = std::min((int)potentialCandidates.size(), NUM_CLUSTER_CANDIDATES_TO_SAMPLE_FROM);
        int selectedIndex = static_cast<int>(std::floor(std::pow(getRandomFraction(), CLUSTER_SELECTION_PULL_STRENGTH) * numCandidatesToConsider));
        
        selectedIndex = std::min(selectedIndex, numCandidatesToConsider - 1);
        if (selectedIndex < 0) selectedIndex = 0;

        int nextCustomer = potentialCandidates[selectedIndex].second;

        selectedCustomersSet.insert(nextCustomer);
        selectedCustomersList.push_back(nextCustomer);
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerPriorities;
    customerPriorities.reserve(customers.size());

    for (int customer_id : customers) {
        customerPriorities.push_back({instance.TW_Width[customer_id], customer_id});
    }

    std::sort(customerPriorities.begin(), customerPriorities.end());

    std::vector<int> reorderedCustomers;
    reorderedCustomers.reserve(customers.size());

    std::vector<std::pair<float, int>> tempPriorities = customerPriorities;

    while (!tempPriorities.empty()) {
        int numCandidatesToConsider = std::min((int)tempPriorities.size(), NUM_SORT_CANDIDATES_TO_SAMPLE_FROM);
        
        int selectedIndex = static_cast<int>(std::floor(std::pow(getRandomFraction(), SORT_SELECTION_PULL_STRENGTH) * numCandidatesToConsider));
        
        selectedIndex = std::min(selectedIndex, numCandidatesToConsider - 1);
        if (selectedIndex < 0) selectedIndex = 0;

        reorderedCustomers.push_back(tempPriorities[selectedIndex].second);
        
        tempPriorities.erase(tempPriorities.begin() + selectedIndex);
    }

    customers = reorderedCustomers;
}