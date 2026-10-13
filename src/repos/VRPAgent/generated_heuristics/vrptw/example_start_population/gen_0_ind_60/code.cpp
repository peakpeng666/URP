#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(15, 30); 
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    std::vector<int> candidateCustomersVec;
    std::unordered_set<int> candidateCustomersSet;

    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initial_customer);
    selectedCustomersVec.push_back(initial_customer);

    for (int neighbor_id : sol.instance.adj[initial_customer]) {
        if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
            if (candidateCustomersSet.find(neighbor_id) == candidateCustomersSet.end()) {
                candidateCustomersVec.push_back(neighbor_id);
                candidateCustomersSet.insert(neighbor_id);
            }
        }
    }

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int next_customer_to_add = -1;
        float choice_prob = getRandomFractionFast();

        if (choice_prob < 0.85 && !candidateCustomersVec.empty()) {
            int attempts = 0;
            int max_attempts_candidate = std::min((int)candidateCustomersVec.size(), 20);
            while(next_customer_to_add == -1 && attempts < max_attempts_candidate) {
                int rand_idx = getRandomNumber(0, candidateCustomersVec.size() - 1);
                int potential_customer = candidateCustomersVec[rand_idx];
                if (selectedCustomersSet.find(potential_customer) == selectedCustomersSet.end()) {
                    next_customer_to_add = potential_customer;
                }
                attempts++;
            }
        }
        
        if (next_customer_to_add == -1) {
            int attempts = 0;
            while ((next_customer_to_add == -1 || selectedCustomersSet.find(next_customer_to_add) != selectedCustomersSet.end()) && attempts < 1000) {
                next_customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (selectedCustomersSet.find(next_customer_to_add) != selectedCustomersSet.end()) {
                for (int c = 1; c <= sol.instance.numCustomers; ++c) {
                    if (selectedCustomersSet.find(c) == selectedCustomersSet.end()) {
                        next_customer_to_add = c;
                        break;
                    }
                }
            }
        }

        if (next_customer_to_add != -1) {
            selectedCustomersSet.insert(next_customer_to_add);
            selectedCustomersVec.push_back(next_customer_to_add);

            for (int neighbor_id : sol.instance.adj[next_customer_to_add]) {
                if (selectedCustomersSet.find(neighbor_id) == selectedCustomersSet.end()) {
                    if (candidateCustomersSet.find(neighbor_id) == candidateCustomersSet.end()) {
                        candidateCustomersVec.push_back(neighbor_id);
                        candidateCustomersSet.insert(neighbor_id);
                    }
                }
            }
        } else {
            break; 
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<int, float>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.TW_Width[customer_id] * 0.6 + instance.serviceTime[customer_id] * 0.4;
        score += getRandomFractionFast() * 0.001; 
        customer_scores.emplace_back(customer_id, score);
    }

    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<int, float>& a, const std::pair<int, float>& b) {
                  return a.second < b.second;
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].first;
    }
}