#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(15, 30);

    if (sol.instance.numCustomers == 0) return {};
    if (numCustomersToRemove > sol.instance.numCustomers) numCustomersToRemove = sol.instance.numCustomers;

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> allPossibleCustomers;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        allPossibleCustomers.push_back(i);
    }
    
    static thread_local std::mt19937 gen(std::random_device{}());
    std::shuffle(allPossibleCustomers.begin(), allPossibleCustomers.end(), gen);

    std::vector<int> candidatesForExpansionVec;
    std::unordered_set<int> candidatesForExpansionSet;

    int currentSeedIdx = 0;

    int seedCustomer = -1;
    while (seedCustomer == -1 && currentSeedIdx < allPossibleCustomers.size()) {
        int potentialSeed = allPossibleCustomers[currentSeedIdx++];
        if (selectedCustomersSet.find(potentialSeed) == selectedCustomersSet.end()) {
            seedCustomer = potentialSeed;
        }
    }
    
    if (seedCustomer != -1) {
        selectedCustomersSet.insert(seedCustomer);
        for (int neighbor : sol.instance.adj[seedCustomer]) {
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() &&
                candidatesForExpansionSet.find(neighbor) == candidatesForExpansionSet.end()) {
                candidatesForExpansionVec.push_back(neighbor);
                candidatesForExpansionSet.insert(neighbor);
            }
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (candidatesForExpansionVec.empty()) {
            int newSeed = -1;
            while (newSeed == -1 && currentSeedIdx < allPossibleCustomers.size()) {
                int potentialSeed = allPossibleCustomers[currentSeedIdx++];
                if (selectedCustomersSet.find(potentialSeed) == selectedCustomersSet.end()) {
                    newSeed = potentialSeed;
                }
            }

            if (newSeed != -1) {
                selectedCustomersSet.insert(newSeed);
                candidatesForExpansionVec.clear();
                candidatesForExpansionSet.clear();
                for (int neighbor : sol.instance.adj[newSeed]) {
                    if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() &&
                        candidatesForExpansionSet.find(neighbor) == candidatesForExpansionSet.end()) {
                        candidatesForExpansionVec.push_back(neighbor);
                        candidatesForExpansionSet.insert(neighbor);
                    }
                }
            } else {
                break;
            }
        }

        if (selectedCustomersSet.size() >= numCustomersToRemove) break;

        int chosenIdx = getRandomNumber(0, candidatesForExpansionVec.size() - 1);
        int chosenCustomer = candidatesForExpansionVec[chosenIdx];

        candidatesForExpansionVec[chosenIdx] = candidatesForExpansionVec.back();
        candidatesForExpansionVec.pop_back();
        candidatesForExpansionSet.erase(chosenCustomer);

        if (selectedCustomersSet.find(chosenCustomer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(chosenCustomer);
            for (int neighbor : sol.instance.adj[chosenCustomer]) {
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() &&
                    candidatesForExpansionSet.find(neighbor) == candidatesForExpansionSet.end()) {
                    candidatesForExpansionVec.push_back(neighbor);
                    candidatesForExpansionSet.insert(neighbor);
                }
            }
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) return;

    std::vector<std::pair<float, int>> scoredCustomers;

    float max_overall_prize = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        if (instance.prizes[i] > max_overall_prize) {
            max_overall_prize = instance.prizes[i];
        }
    }
    float prize_range_for_noise = max_overall_prize > 0 ? max_overall_prize : 1.0f;

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id]; 

        score += getRandomFraction(-0.05f, 0.05f) * prize_range_for_noise; 

        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}