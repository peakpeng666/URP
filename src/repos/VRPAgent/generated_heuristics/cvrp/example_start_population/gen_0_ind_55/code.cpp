#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include <limits>
#include <cmath>
#include "Utils.h"

const int TOP_K_CANDIDATES = 50;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int numCustomersToRemove = std::max(2, getRandomNumber(static_cast<int>(sol.instance.numCustomers * 0.04),
                                                          static_cast<int>(sol.instance.numCustomers * 0.1)));
    if (numCustomersToRemove > 50) numCustomersToRemove = 50;

    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersVec.push_back(seedCustomer);

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        std::vector<std::pair<float, int>> potentialCandidates;

        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (selectedCustomersSet.find(i) == selectedCustomersSet.end()) {
                float min_dist = std::numeric_limits<float>::max();

                for (int selected_cust : selectedCustomersVec) {
                    float dist = sol.instance.distanceMatrix[i][selected_cust];
                    if (dist < min_dist) {
                        min_dist = dist;
                    }
                }
                potentialCandidates.push_back({min_dist, i});
            }
        }

        std::sort(potentialCandidates.begin(), potentialCandidates.end());

        int num_top_k = std::min(static_cast<int>(potentialCandidates.size()), TOP_K_CANDIDATES);
        if (num_top_k == 0) break;

        float rand_frac = getRandomFractionFast();
        float power = 3.0;
        int selected_idx = static_cast<int>(std::floor(num_top_k * std::pow(rand_frac, power)));
        selected_idx = std::min(selected_idx, num_top_k - 1);

        int nextCustomer = potentialCandidates[selected_idx].second;
        selectedCustomersSet.insert(nextCustomer);
        selectedCustomersVec.push_back(nextCustomer);
    }

    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int i = 0; i < customers.size(); ++i) {
        int current_cust = customers[i];
        float sum_dist = 0.0;
        int count = 0;

        for (int j = 0; j < customers.size(); ++j) {
            if (i == j) continue;
            int other_cust = customers[j];
            sum_dist += instance.distanceMatrix[current_cust][other_cust];
            count++;
        }

        float avg_dist = (count > 0) ? (sum_dist / count) : 0.0;
        customer_scores.push_back({avg_dist, current_cust});
    }

    std::sort(customer_scores.begin(), customer_scores.end());

    for (int i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }

    int num_swaps = std::min(static_cast<int>(customers.size() / 2), 5);
    for (int s = 0; s < num_swaps; ++s) {
        if (customers.size() < 2) break;
        int idx1 = getRandomNumber(0, customers.size() - 1);
        int idx2 = getRandomNumber(0, customers.size() - 1);
        std::swap(customers[idx1], customers[idx2]);
    }
}