#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::min, std::sort
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    const Instance& instance = sol.instance;

    int numCustomersToRemove = getRandomNumber(10, 20);

    int initialCustomer = getRandomNumber(1, instance.numCustomers);
    selectedCustomers.insert(initialCustomer);

    std::vector<int> selectedCustomersList;
    selectedCustomersList.push_back(initialCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        bool addedNewCustomerInIteration = false;
        
        int maxPivotAttempts = 5;
        for (int attempt = 0; attempt < maxPivotAttempts && !selectedCustomersList.empty(); ++attempt) {
            int pivotCustomerIdx = getRandomNumber(0, (int)selectedCustomersList.size() - 1);
            int pivotCustomer = selectedCustomersList[pivotCustomerIdx];

            int neighborsToCheck = std::min((int)instance.adj[pivotCustomer].size(), 10);
            
            for (int i = 0; i < neighborsToCheck; ++i) {
                int neighbor = instance.adj[pivotCustomer][i];
                if (neighbor >= 1 && neighbor <= instance.numCustomers && selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    selectedCustomers.insert(neighbor);
                    selectedCustomersList.push_back(neighbor);
                    addedNewCustomerInIteration = true;
                    break;
                }
            }
            if (addedNewCustomerInIteration) {
                break;
            }
        }

        if (!addedNewCustomerInIteration && selectedCustomers.size() < numCustomersToRemove) {
            int randomCustomer;
            int safeguard_counter = 0;
            do {
                randomCustomer = getRandomNumber(1, instance.numCustomers);
                safeguard_counter++;
                if (safeguard_counter > instance.numCustomers * 2) {
                    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
                }
            } while (selectedCustomers.find(randomCustomer) != selectedCustomers.end());
            
            selectedCustomers.insert(randomCustomer);
            selectedCustomersList.push_back(randomCustomer);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    const float PERTURBATION_SCALE = 1.0f; // Scale of random perturbation

    for (int customer_id : customers) {
        float original_tw_width = instance.TW_Width[customer_id];
        float perturbation = getRandomFractionFast() * PERTURBATION_SCALE - (PERTURBATION_SCALE / 2.0f);
        float perturbed_score = original_tw_width + perturbation;
        customerScores.push_back({perturbed_score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first < b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}