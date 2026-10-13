#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 30;
const int NEIGHBORS_TO_CONSIDER_PER_ANCHOR = 10;
const int MAX_ATTEMPTS_BEFORE_RANDOM_FALLBACK = 50;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> potential_anchors;
    int current_anchor_idx = 0;
    int fallback_attempts = 0;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer);
    potential_anchors.push_back(seed_customer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        bool added_new_customer_in_this_iter = false;

        if (potential_anchors.empty()) {
            int next_customer_fallback = getRandomNumber(1, sol.instance.numCustomers);
            while (selectedCustomers.count(next_customer_fallback)) {
                next_customer_fallback = getRandomNumber(1, sol.instance.numCustomers);
            }
            selectedCustomers.insert(next_customer_fallback);
            potential_anchors.push_back(next_customer_fallback);
            added_new_customer_in_this_iter = true;
        } else {
            int anchor_customer = potential_anchors[current_anchor_idx];
            const auto& neighbors = sol.instance.adj[anchor_customer];

            for (int i = 0; i < std::min((int)neighbors.size(), NEIGHBORS_TO_CONSIDER_PER_ANCHOR); ++i) {
                int neighbor = neighbors[i];
                if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    selectedCustomers.insert(neighbor);
                    potential_anchors.push_back(neighbor);
                    added_new_customer_in_this_iter = true;
                    break;
                }
            }
            current_anchor_idx = (current_anchor_idx + 1) % potential_anchors.size();
        }

        if (!added_new_customer_in_this_iter) {
            fallback_attempts++;
            if (fallback_attempts >= MAX_ATTEMPTS_BEFORE_RANDOM_FALLBACK) {
                int next_customer_fallback = getRandomNumber(1, sol.instance.numCustomers);
                while (selectedCustomers.count(next_customer_fallback)) {
                    next_customer_fallback = getRandomNumber(1, sol.instance.numCustomers);
                }
                selectedCustomers.insert(next_customer_fallback);
                potential_anchors.push_back(next_customer_fallback);
                current_anchor_idx = potential_anchors.size() - 1;
                fallback_attempts = 0;
            }
        } else {
            fallback_attempts = 0;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

const float SWAP_PROBABILITY_SORT = 0.05f;

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    float rand_strategy_choice = getRandomFraction();

    if (rand_strategy_choice < 0.45f) {
        for (int customer_id : customers) {
            customer_scores.emplace_back(instance.TW_Width[customer_id], customer_id);
        }
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });
    } else if (rand_strategy_choice < 0.90f) {
        for (int customer_id : customers) {
            customer_scores.emplace_back(instance.demand[customer_id], customer_id);
        }
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
    } else {
        for (int customer_id : customers) {
            customer_scores.emplace_back(instance.distanceMatrix[0][customer_id], customer_id);
        }
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });
    }

    for (size_t i = 0; i + 1 < customer_scores.size(); ++i) {
        if (getRandomFraction() < SWAP_PROBABILITY_SORT) {
            std::swap(customer_scores[i], customer_scores[i+1]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}