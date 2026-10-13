#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"
#include "Solution.h"
#include "Instance.h"
#include "Tour.h"

template<typename T>
void fast_erase_from_vector(std::vector<T>& vec, size_t index) {
    if (index < vec.size()) {
        vec[index] = vec.back();
        vec.pop_back();
    }
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    const Instance& instance = sol.instance;
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> candidatesPool;
    std::unordered_set<int> candidatesPoolSet;

    int min_customers_to_remove = std::max(5, (int)(0.03 * instance.numCustomers));
    int max_customers_to_remove = std::min(20, (int)(0.08 * instance.numCustomers));
    if (min_customers_to_remove > max_customers_to_remove) {
        max_customers_to_remove = min_customers_to_remove;
    }
    int numCustomersToRemove = getRandomNumber(min_customers_to_remove, max_customers_to_remove);
    if (numCustomersToRemove == 0 && instance.numCustomers > 0) numCustomersToRemove = 1;

    if (instance.numCustomers == 0) {
        return {};
    }

    int initialCustomer = getRandomNumber(1, instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);

    const int max_neighbors_to_consider = 10; 
    
    for (size_t i = 0; i < instance.adj[initialCustomer].size() && i < max_neighbors_to_consider; ++i) {
        int neighbor = instance.adj[initialCustomer][i];
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() && candidatesPoolSet.find(neighbor) == candidatesPoolSet.end()) {
            candidatesPool.push_back(neighbor);
            candidatesPoolSet.insert(neighbor);
        }
    }

    const Tour& currentTourInitial = sol.tours[sol.customerToTourMap[initialCustomer]];
    for (int customerInTour : currentTourInitial.customers) {
        if (customerInTour != initialCustomer && selectedCustomersSet.find(customerInTour) == selectedCustomersSet.end() && candidatesPoolSet.find(customerInTour) == candidatesPoolSet.end()) {
            candidatesPool.push_back(customerInTour);
            candidatesPoolSet.insert(customerInTour);
        }
    }
    
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesPool.empty()) {
            int nextRandomCustomer = -1;
            int attempts = 0;
            const int max_attempts = 100;
            while (attempts < max_attempts) {
                int c = getRandomNumber(1, instance.numCustomers);
                if (selectedCustomersSet.find(c) == selectedCustomersSet.end()) {
                    nextRandomCustomer = c;
                    break;
                }
                attempts++;
            }
            if (nextRandomCustomer == -1) { 
                break; 
            }
            selectedCustomersSet.insert(nextRandomCustomer);

            for (size_t i = 0; i < instance.adj[nextRandomCustomer].size() && i < max_neighbors_to_consider; ++i) {
                int neighbor = instance.adj[nextRandomCustomer][i];
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() && candidatesPoolSet.find(neighbor) == candidatesPoolSet.end()) {
                    candidatesPool.push_back(neighbor);
                    candidatesPoolSet.insert(neighbor);
                }
            }
            const Tour& nextTour = sol.tours[sol.customerToTourMap[nextRandomCustomer]];
            for (int customerInTour : nextTour.customers) {
                if (customerInTour != nextRandomCustomer && selectedCustomersSet.find(customerInTour) == selectedCustomersSet.end() && candidatesPoolSet.find(customerInTour) == candidatesPoolSet.end()) {
                    candidatesPool.push_back(customerInTour);
                    candidatesPoolSet.insert(customerInTour);
                }
            }
            continue;
        }

        int idx = 0;
        if (candidatesPool.size() > 1) {
            idx = getRandomNumber(0, std::min((int)candidatesPool.size() - 1, (int)(candidatesPool.size() / 2) + 5)); 
        }
        int customerToSelect = candidatesPool[idx];
        
        fast_erase_from_vector(candidatesPool, idx);
        candidatesPoolSet.erase(customerToSelect);

        if (selectedCustomersSet.find(customerToSelect) != selectedCustomersSet.end()) {
            continue;
        }

        selectedCustomersSet.insert(customerToSelect);

        for (size_t i = 0; i < instance.adj[customerToSelect].size() && i < max_neighbors_to_consider; ++i) {
            int neighbor = instance.adj[customerToSelect][i];
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() && candidatesPoolSet.find(neighbor) == candidatesPoolSet.end()) {
                candidatesPool.push_back(neighbor);
                candidatesPoolSet.insert(neighbor);
            }
        }
        const Tour& currentTour = sol.tours[sol.customerToTourMap[customerToSelect]];
        for (int customerInTour : currentTour.customers) {
            if (customerInTour != customerToSelect && selectedCustomersSet.find(customerInTour) == selectedCustomersSet.end() && candidatesPoolSet.find(customerInTour) == candidatesPoolSet.end()) {
                candidatesPool.push_back(customerInTour);
                candidatesPoolSet.insert(customerInTour);
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    float maxDemand = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        if (instance.demand[i] > maxDemand) {
            maxDemand = (float)instance.demand[i];
        }
    }
    if (maxDemand == 0) maxDemand = 1.0f;

    float maxDepotDist = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        if (instance.distanceMatrix[0][i] > maxDepotDist) {
            maxDepotDist = instance.distanceMatrix[0][i];
        }
    }
    if (maxDepotDist == 0) maxDepotDist = 1.0f;

    const float weightDemand = 0.5f;
    const float weightDepotDist = 0.4f;
    const float weightRandomNoise = 0.1f;

    for (int customerId : customers) {
        float demand = (float)instance.demand[customerId];
        float depotDist = instance.distanceMatrix[0][customerId];

        float normalizedDemand = demand / maxDemand;
        float normalizedDepotDist = depotDist / maxDepotDist;

        float score = (normalizedDemand * weightDemand) +
                      (normalizedDepotDist * weightDepotDist) +
                      (getRandomFractionFast() * weightRandomNoise);

        customerScores.emplace_back(score, customerId);
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}