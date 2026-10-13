#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    const auto& instance = sol.instance;

    int numCustomersToRemove = getRandomNumber(10, 20);

    int firstCustomer = getRandomNumber(1, instance.numCustomers);
    selectedCustomers.insert(firstCustomer);

    std::vector<int> candidatePool;
    std::unordered_set<int> inCandidatePool;

    int neighborsToInitiallyConsider = 10;
    int addedCount = 0;
    for (int neighbor_node : instance.adj[firstCustomer]) {
        if (neighbor_node > 0 && neighbor_node <= instance.numCustomers) {
            if (selectedCustomers.find(neighbor_node) == selectedCustomers.end()) {
                if (inCandidatePool.find(neighbor_node) == inCandidatePool.end()) {
                    candidatePool.push_back(neighbor_node);
                    inCandidatePool.insert(neighbor_node);
                    addedCount++;
                    if (addedCount >= neighborsToInitiallyConsider) break;
                }
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidatePool.empty()) {
            int randomCustomer = getRandomNumber(1, instance.numCustomers);
            while (selectedCustomers.count(randomCustomer)) {
                randomCustomer = getRandomNumber(1, instance.numCustomers);
            }
            selectedCustomers.insert(randomCustomer);

            for (int neighbor_node : instance.adj[randomCustomer]) {
                if (neighbor_node > 0 && neighbor_node <= instance.numCustomers) {
                    if (selectedCustomers.find(neighbor_node) == selectedCustomers.end() &&
                        inCandidatePool.find(neighbor_node) == inCandidatePool.end()) {
                        candidatePool.push_back(neighbor_node);
                        inCandidatePool.insert(neighbor_node);
                    }
                }
            }
            continue;
        }

        int pickedCandidateIdx = getRandomNumber(0, candidatePool.size() - 1);
        int chosenCustomer = candidatePool[pickedCandidateIdx];

        std::swap(candidatePool[pickedCandidateIdx], candidatePool.back());
        candidatePool.pop_back();
        inCandidatePool.erase(chosenCustomer);

        selectedCustomers.insert(chosenCustomer);

        for (int neighbor_node : instance.adj[chosenCustomer]) {
            if (neighbor_node > 0 && neighbor_node <= instance.numCustomers) {
                if (selectedCustomers.find(neighbor_node) == selectedCustomers.end() &&
                    inCandidatePool.find(neighbor_node) == inCandidatePool.end()) {
                    candidatePool.push_back(neighbor_node);
                    inCandidatePool.insert(neighbor_node);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    const float EPSILON_WIDTH = 0.01f; 
    const float RANDOM_INFLUENCE_WEIGHT = 0.2f; 

    for (int customerId : customers) {
        float tw_tightness_score = 1.0f / (instance.TW_Width[customerId] + EPSILON_WIDTH);

        float random_perturbation = getRandomFractionFast() * RANDOM_INFLUENCE_WEIGHT;
        
        float final_score = tw_tightness_score + random_perturbation; 
        scoredCustomers.push_back({final_score, customerId});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}