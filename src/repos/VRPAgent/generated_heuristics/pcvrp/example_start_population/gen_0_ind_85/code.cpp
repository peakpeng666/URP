#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 20);

    int seedCustomer = -1;
    std::vector<int> servedCustomers;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            servedCustomers.push_back(i);
        }
    }

    if (!servedCustomers.empty()) {
        seedCustomer = servedCustomers[getRandomNumber(0, servedCustomers.size() - 1)];
    } else {
        seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }
    selectedCustomers.insert(seedCustomer);

    std::unordered_set<int> candidatePool;
    for (int neighbor : sol.instance.adj[seedCustomer]) {
        if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
            candidatePool.insert(neighbor);
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            int newSeed = -1;
            std::vector<int> unselectedCustomers;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomers.find(i) == selectedCustomers.end()) {
                    unselectedCustomers.push_back(i);
                }
            }

            if (unselectedCustomers.empty()) {
                break;
            }
            newSeed = unselectedCustomers[getRandomNumber(0, unselectedCustomers.size() - 1)];
            selectedCustomers.insert(newSeed);

            for (int neighbor : sol.instance.adj[newSeed]) {
                if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    candidatePool.insert(neighbor);
                }
            }
        } else {
            std::vector<int> candidatesVec(candidatePool.begin(), candidatePool.end());
            int customerToAdd = candidatesVec[getRandomNumber(0, candidatesVec.size() - 1)];

            selectedCustomers.insert(customerToAdd);
            candidatePool.erase(customerToAdd);

            for (int neighbor : sol.instance.adj[customerToAdd]) {
                if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    candidatePool.insert(neighbor);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    float max_prize = 0.0;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        if (instance.prizes[i] > max_prize) {
            max_prize = instance.prizes[i];
        }
    }
    if (max_prize == 0.0) max_prize = 1.0f;

    for (int customer_id : customers) {
        float base_score = instance.prizes[customer_id] - instance.distanceMatrix[0][customer_id];

        float noise_range = 0.05f * max_prize;
        float noise = getRandomFraction(-noise_range, noise_range);

        float final_score = base_score + noise;
        customerScores.emplace_back(final_score, customer_id);
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}