#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include <utility>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;

    int numCustomersToTarget = getRandomNumber(10, 25);

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    selectedCustomers.insert(getRandomNumber(1, sol.instance.numCustomers));

    while (selectedCustomers.size() < numCustomersToTarget) {
        int c_anchor;
        if (selectedCustomers.empty()) {
            c_anchor = getRandomNumber(1, sol.instance.numCustomers);
        } else {
            int random_idx = getRandomNumber(0, (int)selectedCustomers.size() - 1);
            auto it = selectedCustomers.begin();
            std::advance(it, random_idx);
            c_anchor = *it;
        }

        bool found_new = false;
        int num_neighbors_to_try = std::min((int)sol.instance.adj[c_anchor].size(), 10 + getRandomNumber(0, 5));

        for (int i = 0; i < num_neighbors_to_try; ++i) {
            int c_candidate = sol.instance.adj[c_anchor][i];
            if (c_candidate != 0 && selectedCustomers.find(c_candidate) == selectedCustomers.end()) {
                float prob_acceptance = 1.0f - ((float)i / num_neighbors_to_try * 0.5f);
                if (getRandomFractionFast() < prob_acceptance || selectedCustomers.size() < 3) {
                    selectedCustomers.insert(c_candidate);
                    found_new = true;
                    break;
                }
            }
        }

        if (!found_new) {
            if (sol.instance.numCustomers > 0) {
                selectedCustomers.insert(getRandomNumber(1, sol.instance.numCustomers));
            } else {
                break;
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float effective_demand = static_cast<float>(instance.demand[customer_id]);
        float effective_prize = instance.prizes[customer_id];

        float score = effective_prize / (1.0f + effective_demand);

        score += (getRandomFractionFast() * 0.1f - 0.05f);

        customer_scores.emplace_back(score, customer_id);
    }

    std::sort(customer_scores.begin(), customer_scores.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}