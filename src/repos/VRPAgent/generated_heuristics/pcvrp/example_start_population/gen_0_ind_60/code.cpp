#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    int numCustomersToRemove = getRandomNumber(20, 50); 

    if (sol.instance.numCustomers < numCustomersToRemove) {
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            selectedCustomersSet.insert(i);
        }
        return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
    }

    int centralCustomer = getRandomNumber(1, sol.instance.numCustomers); 

    int numCandidatesPool = std::min((int)sol.instance.adj[centralCustomer].size() + 1, numCustomersToRemove * 3);

    std::vector<int> candidatePool;
    candidatePool.reserve(numCandidatesPool);

    candidatePool.push_back(centralCustomer); 

    for (int i = 0; candidatePool.size() < numCandidatesPool && i < sol.instance.adj[centralCustomer].size(); ++i) {
        candidatePool.push_back(sol.instance.adj[centralCustomer][i]);
    }

    static thread_local std::mt19937 gen_select(std::random_device{}());
    std::shuffle(candidatePool.begin(), candidatePool.end(), gen_select);

    for (int customer_id : candidatePool) {
        if (selectedCustomersSet.size() < numCustomersToRemove) {
            selectedCustomersSet.insert(customer_id);
        } else {
            break;
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        selectedCustomersSet.insert(randomCustomer);
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    for (int customer_id : customers) {
        float base_score = 0.0;
        if (instance.demand[customer_id] > 0) {
            base_score = instance.prizes[customer_id] / static_cast<float>(instance.demand[customer_id]);
        } else {
            base_score = instance.prizes[customer_id];
        }

        float stochastic_factor = 1.0 + (getRandomFractionFast() * 0.2 - 0.1); 
        float final_score = base_score * stochastic_factor;

        scoredCustomers.push_back({final_score, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}