#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 20);

    std::vector<int> selectedCustomersVec;
    std::vector<bool> isSelected(sol.instance.numCustomers + 1, false);

    std::vector<int> candidatePoolVec;
    std::vector<bool> inCandidatePool(sol.instance.numCustomers + 1, false);

    if (numCustomersToRemove <= 0 || sol.instance.numCustomers == 0) {
        return selectedCustomersVec;
    }

    int current_customer_count = 0;

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersVec.push_back(seed_customer);
    isSelected[seed_customer] = true;
    current_customer_count++;

    for (int neighbor : sol.instance.adj[seed_customer]) {
        if (!isSelected[neighbor] && !inCandidatePool[neighbor]) {
            candidatePoolVec.push_back(neighbor);
            inCandidatePool[neighbor] = true;
            if (candidatePoolVec.size() >= 20) break;
        }
    }

    while (current_customer_count < numCustomersToRemove) {
        if (candidatePoolVec.empty()) {
            bool reseeded_successfully = false;
            if (!selectedCustomersVec.empty()) {
                int reseed_customer = selectedCustomersVec[getRandomNumber(0, selectedCustomersVec.size() - 1)];
                for (int neighbor : sol.instance.adj[reseed_customer]) {
                    if (!isSelected[neighbor] && !inCandidatePool[neighbor]) {
                        candidatePoolVec.push_back(neighbor);
                        inCandidatePool[neighbor] = true;
                        reseeded_successfully = true;
                        if (candidatePoolVec.size() >= 20) break;
                    }
                }
            }

            if (!reseeded_successfully && candidatePoolVec.empty()) {
                int new_random_seed = -1;
                for (int i = 0; i < sol.instance.numCustomers * 2; ++i) {
                    int potential_seed = getRandomNumber(1, sol.instance.numCustomers);
                    if (!isSelected[potential_seed]) {
                        new_random_seed = potential_seed;
                        break;
                    }
                }

                if (new_random_seed != -1) {
                    selectedCustomersVec.push_back(new_random_seed);
                    isSelected[new_random_seed] = true;
                    current_customer_count++;
                    if (current_customer_count == numCustomersToRemove) break;

                    for (int neighbor : sol.instance.adj[new_random_seed]) {
                        if (!isSelected[neighbor] && !inCandidatePool[neighbor]) {
                            candidatePoolVec.push_back(neighbor);
                            inCandidatePool[neighbor] = true;
                            if (candidatePoolVec.size() >= 20) break;
                        }
                    }
                } else {
                    break;
                }
            }
        }
        
        if (candidatePoolVec.empty()) {
            break;
        }

        int idx_in_pool = getRandomNumber(0, candidatePoolVec.size() - 1);
        int next_customer = candidatePoolVec[idx_in_pool];

        candidatePoolVec[idx_in_pool] = candidatePoolVec.back();
        inCandidatePool[next_customer] = false;
        candidatePoolVec.pop_back();

        if (!isSelected[next_customer]) {
            selectedCustomersVec.push_back(next_customer);
            isSelected[next_customer] = true;
            current_customer_count++;

            for (int neighbor : sol.instance.adj[next_customer]) {
                if (!isSelected[neighbor] && !inCandidatePool[neighbor]) {
                    candidatePoolVec.push_back(neighbor);
                    inCandidatePool[neighbor] = true;
                    if (candidatePoolVec.size() >= 20) break;
                }
            }
        }
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int c_id : customers) {
        float current_score = 0.0f;
        for (int other_c_id : customers) {
            if (c_id != other_c_id) {
                current_score += instance.distanceMatrix[c_id][other_c_id];
            }
        }
        current_score += 10.0f * getRandomFractionFast();

        customer_scores.push_back({current_score, c_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}