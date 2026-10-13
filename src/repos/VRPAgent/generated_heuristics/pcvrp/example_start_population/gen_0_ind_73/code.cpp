#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 15;
const int MAX_CUSTOMERS_TO_REMOVE = 30;
const float P_UNVISITED_SEED = 0.25f;
const float P_RANDOM_JUMP = 0.15f;
const int MAX_NEIGHBOR_SEARCH_DEPTH = 10;

const float PRIZE_WEIGHT = 1.0f;
const float DIST_TO_DEPOT_WEIGHT = 0.5f;
const float DEMAND_WEIGHT = 0.1f;
const float STOCHASTIC_PERTURBATION_RANGE = 0.1f;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> sourceCustomers;

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    int initial_seed = -1;
    if (getRandomFractionFast() < P_UNVISITED_SEED) {
        for (int i = 0; i < 50; ++i) {
            int c = getRandomNumber(1, sol.instance.numCustomers);
            if (sol.customerToTourMap[c] == -1) {
                initial_seed = c;
                break;
            }
        }
    }
    if (initial_seed == -1) {
        for (int i = 0; i < 50; ++i) {
            int c = getRandomNumber(1, sol.instance.numCustomers);
            if (sol.customerToTourMap[c] != -1) {
                initial_seed = c;
                break;
            }
        }
    }
    if (initial_seed == -1) {
        initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    }
    selectedCustomers.insert(initial_seed);
    sourceCustomers.push_back(initial_seed);

    while (selectedCustomers.size() < numCustomersToRemove) {
        int next_customer = -1;
        
        if (getRandomFractionFast() < P_RANDOM_JUMP || sourceCustomers.empty()) {
            for (int i = 0; i < 50; ++i) {
                int c = getRandomNumber(1, sol.instance.numCustomers);
                if (selectedCustomers.find(c) == selectedCustomers.end()) {
                    next_customer = c;
                    break;
                }
            }
        } else {
            int anchor_customer_idx = getRandomNumber(0, sourceCustomers.size() - 1);
            int anchor_customer = sourceCustomers[anchor_customer_idx];
            
            int best_neighbor_candidate = -1;
            
            for (int i = 0; i < std::min((int)sol.instance.adj[anchor_customer].size(), MAX_NEIGHBOR_SEARCH_DEPTH); ++i) {
                int neighbor = sol.instance.adj[anchor_customer][i];
                if (selectedCustomers.find(neighbor) == selectedCustomers.end()) {
                    if (best_neighbor_candidate == -1) {
                        best_neighbor_candidate = neighbor;
                    }
                    if (sol.customerToTourMap[neighbor] == -1 && getRandomFractionFast() < 0.3f) {
                        next_customer = neighbor;
                        break;
                    }
                }
            }
            if (next_customer == -1) {
                next_customer = best_neighbor_candidate;
            }
        }

        if (next_customer != -1) {
            selectedCustomers.insert(next_customer);
            sourceCustomers.push_back(next_customer);
            if (sourceCustomers.size() > numCustomersToRemove * 2) {
                sourceCustomers.erase(sourceCustomers.begin() + getRandomNumber(0, sourceCustomers.size() - 1));
            }
        } else {
            break;
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    for (int customer_id : customers) {
        float current_prize = instance.prizes[customer_id];
        float current_demand = instance.demand[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id];

        float score = current_prize * PRIZE_WEIGHT - 
                      dist_to_depot * DIST_TO_DEPOT_WEIGHT - 
                      current_demand * DEMAND_WEIGHT;

        score += getRandomFraction(-STOCHASTIC_PERTURBATION_RANGE, STOCHASTIC_PERTURBATION_RANGE);

        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}