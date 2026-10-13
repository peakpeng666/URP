#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <numeric>
#include "Utils.h"
#include "Instance.h"
#include "Solution.h"
#include "Tour.h"

constexpr int MIN_CUSTOMERS_TO_REMOVE = 15;
constexpr int MAX_CUSTOMERS_TO_REMOVE = 40;
constexpr float PROB_LOCAL_EXPANSION = 0.8f;
constexpr int NUM_ADJ_NEIGHBORS_CONSIDER = 10;

constexpr float PRIZE_WEIGHT = 1.0f;
constexpr float DEMAND_WEIGHT = 0.5f;
constexpr float NOISE_MAGNITUDE_PRIZE = 0.1f;
constexpr float NOISE_MAGNITUDE_DEMAND = 0.05f;


std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;
    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    int seedCustomer;
    std::vector<int> visitedCustomers;
    if (!sol.tours.empty()) {
        for (const auto& tour : sol.tours) {
            for (int customer : tour.customers) {
                visitedCustomers.push_back(customer);
            }
        }
    }
    
    if (!visitedCustomers.empty() && getRandomFraction() >= 0.2f) {
        seedCustomer = visitedCustomers[getRandomNumber(0, visitedCustomers.size() - 1)];
    } else {
        seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersList.push_back(seedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int candidateCustomer = -1;

        if (getRandomFraction() < PROB_LOCAL_EXPANSION) {
            int pivotCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];
            
            if (!sol.instance.adj[pivotCustomer].empty()) {
                int neighborIdx = getRandomNumber(0, std::min((int)sol.instance.adj[pivotCustomer].size() - 1, NUM_ADJ_NEIGHBORS_CONSIDER - 1));
                candidateCustomer = sol.instance.adj[pivotCustomer][neighborIdx];
            } else {
                candidateCustomer = getRandomNumber(1, sol.instance.numCustomers);
            }
        } else {
            candidateCustomer = getRandomNumber(1, sol.instance.numCustomers);
        }

        if (selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(candidateCustomer);
            selectedCustomersList.push_back(candidateCustomer);
        }
    }

    return selectedCustomersList;
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customerIdx : customers) {
        float prizeComponent = instance.prizes[customerIdx] * (1.0f + getRandomFraction(-NOISE_MAGNITUDE_PRIZE, NOISE_MAGNITUDE_PRIZE));
        float demandComponent = instance.demand[customerIdx] * (1.0f + getRandomFraction(-NOISE_MAGNITUDE_DEMAND, NOISE_MAGNITUDE_DEMAND));

        float score = PRIZE_WEIGHT * prizeComponent - DEMAND_WEIGHT * demandComponent;

        customerScores.push_back({score, customerIdx});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}