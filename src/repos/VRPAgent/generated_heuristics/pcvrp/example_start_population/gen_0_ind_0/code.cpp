#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort, std::swap
#include <vector>    // For std::vector
#include <utility>   // For std::pair
#include <cmath>     // For std::min, std::fmax

#include "Utils.h" // For getRandomNumber, getRandomFractionFast, argsort

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selectedCustomersVec;
    std::unordered_set<int> selectedCustomersSet;

    int numCustomersToRemove = getRandomNumber(10, 25); 

    std::vector<int> candidateCustomers;
    std::unordered_set<int> candidateCustomersSet;

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersVec.push_back(seed_customer);
    selectedCustomersSet.insert(seed_customer);

    int num_initial_neighbors_to_consider = std::min((int)sol.instance.adj[seed_customer].size(), 10);
    for (int i = 0; i < num_initial_neighbors_to_consider; ++i) {
        int neighbor = sol.instance.adj[seed_customer][i];
        if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
            if (candidateCustomersSet.find(neighbor) == candidateCustomersSet.end()) {
                candidateCustomers.push_back(neighbor);
                candidateCustomersSet.insert(neighbor);
            }
        }
    }

    while (selectedCustomersVec.size() < numCustomersToRemove && !candidateCustomers.empty()) {
        int pick_idx = getRandomNumber(0, candidateCustomers.size() - 1);
        int new_customer = candidateCustomers[pick_idx];

        std::swap(candidateCustomers[pick_idx], candidateCustomers.back());
        candidateCustomers.pop_back();
        candidateCustomersSet.erase(new_customer);

        if (selectedCustomersSet.find(new_customer) != selectedCustomersSet.end()) {
            continue;
        }

        selectedCustomersVec.push_back(new_customer);
        selectedCustomersSet.insert(new_customer);

        int num_neighbors_to_consider = std::min((int)sol.instance.adj[new_customer].size(), 10);
        for (int i = 0; i < num_neighbors_to_consider; ++i) {
            int neighbor = sol.instance.adj[new_customer][i];
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (candidateCustomersSet.find(neighbor) == candidateCustomersSet.end()) {
                    candidateCustomers.push_back(neighbor);
                    candidateCustomersSet.insert(neighbor);
                }
            }
        }
    }

    while (selectedCustomersVec.size() < numCustomersToRemove) {
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomersSet.find(randomCustomer) == selectedCustomersSet.end()) {
            selectedCustomersVec.push_back(randomCustomer);
            selectedCustomersSet.insert(randomCustomer);
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id] / (instance.demand[customer_id] + 1.0f);

        float avg_dist_to_closest = 0.0f;
        int num_neighbors_to_consider = std::min((int)instance.adj[customer_id].size(), 5); 
        
        if (num_neighbors_to_consider > 0) {
            for (int i = 0; i < num_neighbors_to_consider; ++i) {
                int neighbor_node = instance.adj[customer_id][i];
                avg_dist_to_closest += instance.distanceMatrix[customer_id][neighbor_node];
            }
            avg_dist_to_closest /= num_neighbors_to_consider;
            
            score += 1.0f / (std::fmax(avg_dist_to_closest, 0.1f) + 1.0f); 
        }

        score += getRandomFractionFast() * 0.1f * score;

        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}