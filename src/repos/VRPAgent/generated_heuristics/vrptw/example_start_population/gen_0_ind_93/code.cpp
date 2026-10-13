#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <tuple>
#include <iterator>
#include <limits> // For std::numeric_limits
#include "Utils.h"

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove <= 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    }
    if (sol.instance.numCustomers == 0) return {};

    int firstCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(firstCustomer);

    const float PROB_NEW_SEED = 0.25f; 
    const int ADJ_LIST_SEARCH_LIMIT = 50; 

    while (selectedCustomers.size() < numCustomersToRemove) {
        int nextCustomerToSelect = -1;

        if (getRandomFraction() < PROB_NEW_SEED) {
            nextCustomerToSelect = getRandomNumber(1, sol.instance.numCustomers);
        } else {
            int pivotCustomer = -1;
            int randIdx = getRandomNumber(0, selectedCustomers.size() - 1);
            int currentIdx = 0;
            for (int cust : selectedCustomers) {
                if (currentIdx == randIdx) {
                    pivotCustomer = cust;
                    break;
                }
                currentIdx++;
            }

            bool foundNeighbor = false;
            if (pivotCustomer >= 0 && pivotCustomer < sol.instance.adj.size()) { 
                for (int i = 0; i < std::min((int)sol.instance.adj[pivotCustomer].size(), ADJ_LIST_SEARCH_LIMIT); ++i) {
                    int neighbor = sol.instance.adj[pivotCustomer][i];
                    if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                        nextCustomerToSelect = neighbor;
                        foundNeighbor = true;
                        break;
                    }
                }
            }
            
            if (!foundNeighbor) {
                nextCustomerToSelect = getRandomNumber(1, sol.instance.numCustomers);
            }
        }

        if (nextCustomerToSelect != -1 && selectedCustomers.find(nextCustomerToSelect) == selectedCustomers.end()) {
            selectedCustomers.insert(nextCustomerToSelect);
        } else {
            while (true) {
                int fallbackCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(fallbackCustomer) == selectedCustomers.end()) {
                    selectedCustomers.insert(fallbackCustomer);
                    break;
                }
                if (selectedCustomers.size() >= numCustomersToRemove) break; 
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Ordering of removed customers heuristic
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float PROB_RANDOM_SHUFFLE = 0.10f; 
    if (getRandomFraction() < PROB_RANDOM_SHUFFLE) {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::tuple<float, float, float, int>> sortableCustomers;
    sortableCustomers.reserve(customers.size());

    for (int customerId : customers) {
        if (customerId >= 0 && customerId < instance.numNodes) { 
             sortableCustomers.emplace_back(
                instance.startTW[customerId],
                instance.endTW[customerId],
                instance.distanceMatrix[0][customerId], 
                customerId
            );
        } else {
            sortableCustomers.emplace_back(
                std::numeric_limits<float>::max(), 
                std::numeric_limits<float>::max(), 
                std::numeric_limits<float>::max(), 
                customerId
            );
        }
    }

    std::sort(sortableCustomers.begin(), sortableCustomers.end());

    for (size_t i = 0; i < sortableCustomers.size(); ++i) {
        customers[i] = std::get<3>(sortableCustomers[i]); 
    }

    const float PROB_REVERSE_SORT = 0.10f; 
    if (getRandomFraction() < PROB_REVERSE_SORT) {
        std::reverse(customers.begin(), customers.end());
    }
}