#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include <cmath>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, std::min((int)(sol.instance.numCustomers * 0.05), 30));
    numCustomersToRemove = std::max(1, numCustomersToRemove); 

    int served_customers_count = 0;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            served_customers_count++;
        }
    }
    numCustomersToRemove = std::min(numCustomersToRemove, served_customers_count);

    if (numCustomersToRemove == 0) {
        return {};
    }

    std::vector<int> candidatesForExpansion;
    candidatesForExpansion.reserve(numCustomersToRemove);

    int initial_seed = getRandomNumber(1, sol.instance.numCustomers);
    int attempts = 0;
    while (sol.customerToTourMap[initial_seed] == -1 && attempts < 1000 && served_customers_count > 0) {
        initial_seed = getRandomNumber(1, sol.instance.numCustomers);
        attempts++;
    }
    if (sol.customerToTourMap[initial_seed] != -1) {
        selectedCustomers.insert(initial_seed);
        candidatesForExpansion.push_back(initial_seed);
    } else {
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            if (sol.customerToTourMap[i] != -1) {
                selectedCustomers.insert(i);
                candidatesForExpansion.push_back(i);
                break;
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        bool added_customer_in_iteration = false;

        if (!candidatesForExpansion.empty() && getRandomFractionFast() < 0.85f) {
            int c_base = candidatesForExpansion[getRandomNumber(0, candidatesForExpansion.size() - 1)];

            for (int k = 0; k < std::min((int)sol.instance.adj[c_base].size(), 15); ++k) {
                int n_cand = sol.instance.adj[c_base][k];

                if (n_cand != 0 && !selectedCustomers.count(n_cand) && sol.customerToTourMap[n_cand] != -1) {
                    selectedCustomers.insert(n_cand);
                    candidatesForExpansion.push_back(n_cand);
                    added_customer_in_iteration = true;
                    break;
                }
            }
        }

        if (!added_customer_in_iteration) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            attempts = 0;
            while ((selectedCustomers.count(new_seed) || sol.customerToTourMap[new_seed] == -1) && attempts < 1000 && selectedCustomers.size() < served_customers_count) {
                new_seed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            }
            if (!selectedCustomers.count(new_seed) && sol.customerToTourMap[new_seed] != -1) {
                selectedCustomers.insert(new_seed);
                candidatesForExpansion.push_back(new_seed);
            } else if (selectedCustomers.size() < numCustomersToRemove) {
                bool found_fallback = false;
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (!selectedCustomers.count(i) && sol.customerToTourMap[i] != -1) {
                        selectedCustomers.insert(i);
                        candidatesForExpansion.push_back(i);
                        found_fallback = true;
                        break;
                    }
                }
                if (!found_fallback) {
                    break;
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

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float score = 0.0f;

        score += (100.0f / (instance.TW_Width[customer_id] + 1e-6f));

        score += instance.distanceMatrix[0][customer_id] * 0.01f;

        score += instance.demand[customer_id] * 0.5f;

        score += instance.serviceTime[customer_id] * 0.1f;

        score += getRandomFraction(-0.01f, 0.01f);

        scored_customers.push_back({score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }

    if (getRandomFractionFast() < 0.15f) {
        std::reverse(customers.begin(), customers.end());
    }
}