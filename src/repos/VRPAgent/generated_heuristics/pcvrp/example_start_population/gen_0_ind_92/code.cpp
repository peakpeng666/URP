#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <limits>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int minCustomersToRemove = std::max(5, (int)(0.01 * sol.instance.numCustomers));
    int maxCustomersToRemove = std::min(50, (int)(0.04 * sol.instance.numCustomers));
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int currentCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(currentCustomer);
    selectedCustomersList.push_back(currentCustomer);

    while (selectedCustomersList.size() < numCustomersToRemove) {
        bool expanded = false;
        int numNeighbors = sol.instance.adj[currentCustomer].size();

        if (numNeighbors > 0) {
            int numNeighborsToTry = std::min(numNeighbors, getRandomNumber(3, 10));
            
            std::vector<int> candidates;
            for (int i = 0; i < numNeighborsToTry; ++i) {
                int neighbor = sol.instance.adj[currentCustomer][i];
                if (!selectedCustomersSet.count(neighbor)) {
                    candidates.push_back(neighbor);
                }
            }

            if (!candidates.empty()) {
                int chosenNeighbor = candidates[getRandomNumber(0, candidates.size() - 1)];
                selectedCustomersSet.insert(chosenNeighbor);
                selectedCustomersList.push_back(chosenNeighbor);
                currentCustomer = chosenNeighbor;
                expanded = true;
            }
        }

        if (!expanded || getRandomFraction() < 0.15) {
            if (!selectedCustomersList.empty()) {
                currentCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];
            } else {
                currentCustomer = getRandomNumber(1, sol.instance.numCustomers);
                while (selectedCustomersSet.count(currentCustomer)) {
                    currentCustomer = getRandomNumber(1, sol.instance.numCustomers);
                }
                selectedCustomersSet.insert(currentCustomer);
                selectedCustomersList.push_back(currentCustomer);
            }
        }
    }
    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());
    for (int c : customers) {
        float score = instance.prizes[c] * 10.0F - instance.demand[c] * 1.0F;
        score += getRandomFractionFast() * 0.1F;
        customer_scores.push_back({score, c});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    std::vector<int> temp_customers_sorted_by_profitability;
    temp_customers_sorted_by_profitability.reserve(customers.size());
    for (const auto& p : customer_scores) {
        temp_customers_sorted_by_profitability.push_back(p.second);
    }

    std::vector<int> final_sorted_customers;
    final_sorted_customers.reserve(customers.size());
    std::unordered_set<int> remaining_customers(temp_customers_sorted_by_profitability.begin(), temp_customers_sorted_by_profitability.end());

    int current_customer_idx_in_profit_list = getRandomNumber(0, temp_customers_sorted_by_profitability.size() - 1);
    int current_customer = temp_customers_sorted_by_profitability[current_customer_idx_in_profit_list];
    
    final_sorted_customers.push_back(current_customer);
    remaining_customers.erase(current_customer);

    while (!remaining_customers.empty()) {
        bool found_related_customer = false;
        int next_customer_candidate = -1;
        
        int num_neighbors_to_check = std::min((int)instance.adj[current_customer].size(), getRandomNumber(3, 10));

        std::vector<int> potential_next_neighbors;
        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor = instance.adj[current_customer][i];
            if (remaining_customers.count(neighbor)) {
                potential_next_neighbors.push_back(neighbor);
            }
        }
        
        if (!potential_next_neighbors.empty()) {
            next_customer_candidate = potential_next_neighbors[getRandomNumber(0, potential_next_neighbors.size() - 1)];
            found_related_customer = true;
        }

        if (!found_related_customer || getRandomFractionFast() < 0.2F) {
            auto it = remaining_customers.begin();
            std::advance(it, getRandomNumber(0, remaining_customers.size() - 1));
            next_customer_candidate = *it;
        }
        
        final_sorted_customers.push_back(next_customer_candidate);
        remaining_customers.erase(next_customer_candidate);
        current_customer = next_customer_candidate;
    }

    customers = final_sorted_customers;
}