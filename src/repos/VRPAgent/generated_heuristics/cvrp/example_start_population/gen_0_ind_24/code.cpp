#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers_set;
    std::vector<int> selectedCustomers_vec;

    int numCustomersToRemove = getRandomNumber(sol.instance.numCustomers / 50, sol.instance.numCustomers / 25);
    numCustomersToRemove = std::max(5, std::min(numCustomersToRemove, 30));

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers_set.insert(initialCustomer);
    selectedCustomers_vec.push_back(initialCustomer);

    if (numCustomersToRemove == 1) {
        return selectedCustomers_vec;
    }

    int maxAdjNeighborsToConsider = 15;
    int maxAttemptsForNewCustomer = 50;

    for (int i = 1; i < numCustomersToRemove; ++i) {
        bool customerAdded = false;
        for (int attempt = 0; attempt < maxAttemptsForNewCustomer; ++attempt) {
            int pivotIndex = getRandomNumber(0, selectedCustomers_vec.size() - 1);
            int pivotCustomer = selectedCustomers_vec[pivotIndex];

            std::vector<int> potentialCandidates;
            const auto& adj_list = sol.instance.adj[pivotCustomer];

            for (size_t k = 0; k < adj_list.size() && k < maxAdjNeighborsToConsider; ++k) {
                int neighbor = adj_list[k];
                if (neighbor == 0) { // Skip depot if present in adjacency list
                    continue;
                }
                if (selectedCustomers_set.find(neighbor) == selectedCustomers_set.end()) {
                    int numRepeats = maxAdjNeighborsToConsider - k; 
                    for (int r = 0; r < numRepeats; ++r) {
                        potentialCandidates.push_back(neighbor);
                    }
                }
            }

            if (!potentialCandidates.empty()) {
                int chosenCandidate = potentialCandidates[getRandomNumber(0, potentialCandidates.size() - 1)];
                selectedCustomers_set.insert(chosenCandidate);
                selectedCustomers_vec.push_back(chosenCandidate);
                customerAdded = true;
                break;
            }
        }
        
        if (!customerAdded) {
            int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers_set.count(randomCustomer)) {
                randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers_set.insert(randomCustomer);
            selectedCustomers_vec.push_back(randomCustomer);
        }
    }
    return selectedCustomers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores; 
    int k_neighbors_for_isolation_score = 3; 
    float demand_weight = 0.6; 
    float isolation_weight = 0.4; 
    float stochastic_perturbation_factor = 0.05; 

    for (int customer_id : customers) {
        float isolation_distance_avg = 0.0;
        int num_neighbors_considered = 0;
        const auto& adj_list = instance.adj[customer_id]; 

        for (size_t k = 0; k < adj_list.size() && k < k_neighbors_for_isolation_score; ++k) {
            int neighbor_id = adj_list[k];
            if (neighbor_id == 0) { // Skip depot
                continue;
            }
            if (customer_id >= 0 && customer_id < instance.numNodes && 
                neighbor_id >= 0 && neighbor_id < instance.numNodes) {
                isolation_distance_avg += instance.distanceMatrix[customer_id][neighbor_id];
                num_neighbors_considered++;
            }
        }

        if (num_neighbors_considered > 0) {
            isolation_distance_avg /= static_cast<float>(num_neighbors_considered);
        } else {
            isolation_distance_avg = 1e9; 
        }

        float score = demand_weight * instance.demand[customer_id] + isolation_weight * isolation_distance_avg;
        
        score += getRandomFractionFast() * stochastic_perturbation_factor; 

        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}