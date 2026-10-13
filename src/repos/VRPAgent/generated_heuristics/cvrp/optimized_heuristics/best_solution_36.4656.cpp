#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomers = sol.instance.numCustomers;
    if (numCustomers == 0) {
        return {};
    }

    int minCustomersToRemove = std::max(10, numCustomers / 50);
    int maxCustomersToRemove = std::min(30, numCustomers / 10);
    
    if (maxCustomersToRemove < minCustomersToRemove) {
        maxCustomersToRemove = minCustomersToRemove;
    }
    if (minCustomersToRemove == 0 && numCustomers > 0) {
        minCustomersToRemove = 1;
        if (maxCustomersToRemove == 0) maxCustomersToRemove = 1;
    }
    
    int numCustomersToTarget = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToTarget == 0) {
        return {};
    }

    std::vector<bool> is_selected_flag(numCustomers + 1, false);
    std::vector<int> selectedCustomersList;
    std::vector<int> candidateCustomers;

    int initialSeedCustomer = getRandomNumber(1, numCustomers);
    is_selected_flag[initialSeedCustomer] = true;
    selectedCustomersList.push_back(initialSeedCustomer);
    candidateCustomers.push_back(initialSeedCustomer);

    float diffusionProbability = 0.7f + getRandomFractionFast() * 0.2f; 
    float globalRandomJumpChance = 0.1f + getRandomFractionFast() * 0.05f; 

    while (selectedCustomersList.size() < static_cast<size_t>(numCustomersToTarget)) {
        bool jumped = false;
        if (candidateCustomers.empty() || getRandomFractionFast() < globalRandomJumpChance) {
            int newSeed = -1;
            int attempts = 0;
            const int maxJumpAttempts = numCustomers * 2; 
            while (attempts < maxJumpAttempts && selectedCustomersList.size() < static_cast<size_t>(numCustomers)) {
                int potentialSeed = getRandomNumber(1, numCustomers);
                if (!is_selected_flag[potentialSeed]) {
                    newSeed = potentialSeed;
                    break;
                }
                attempts++;
            }
            if (newSeed != -1) {
                is_selected_flag[newSeed] = true;
                selectedCustomersList.push_back(newSeed);
                candidateCustomers.push_back(newSeed);
                jumped = true;
                if (selectedCustomersList.size() == static_cast<size_t>(numCustomersToTarget)) {
                    break;
                }
            } else {
                break; 
            }
        }

        if (!jumped && !candidateCustomers.empty()) {
            int randIdx = getRandomNumber(0, static_cast<int>(candidateCustomers.size() - 1));
            int currentCustomer = candidateCustomers[randIdx];

            std::swap(candidateCustomers[randIdx], candidateCustomers.back());
            candidateCustomers.pop_back();

            if (currentCustomer > 0 && currentCustomer <= numCustomers) { 
                for (int neighborId : sol.instance.adj[currentCustomer]) {
                    if (neighborId > 0 && neighborId <= numCustomers && !is_selected_flag[neighborId]) {
                        if (getRandomFractionFast() < diffusionProbability) {
                            is_selected_flag[neighborId] = true;
                            selectedCustomersList.push_back(neighborId);
                            candidateCustomers.push_back(neighborId);
                            if (selectedCustomersList.size() == static_cast<size_t>(numCustomersToTarget)) {
                                break;
                            }
                        }
                    }
                }
            }
            if (selectedCustomersList.size() == static_cast<size_t>(numCustomersToTarget)) {
                break;
            }
        }
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int strategy_choice = getRandomNumber(0, 7);

    static thread_local std::mt19937 gen(std::random_device{}());

    if (strategy_choice == 0) {
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    bool sort_ascending = (getRandomNumber(0, 1) == 0);

    struct CustomerScore {
        int id;
        float score;
    };
    std::vector<CustomerScore> customerScores;
    customerScores.reserve(customers.size());

    float max_dist_to_depot_subset = 0.0f;
    float max_demand_subset = 0.0f;
    if (strategy_choice == 5) {
        for (int customer_id : customers) {
            max_dist_to_depot_subset = std::max(max_dist_to_depot_subset, static_cast<float>(instance.distanceMatrix[0][customer_id]));
            max_demand_subset = std::max(max_demand_subset, static_cast<float>(instance.demand[customer_id]));
        }
    }

    if (strategy_choice == 1) { 
        for (int customerId : customers) {
            customerScores.push_back({customerId, static_cast<float>(instance.distanceMatrix[0][customerId])});
        }
    } else if (strategy_choice == 2) { 
        for (int customerId : customers) {
            customerScores.push_back({customerId, static_cast<float>(instance.demand[customerId])});
        }
    } else if (strategy_choice == 3) { 
        int anchorCustomer = customers[getRandomNumber(0, static_cast<int>(customers.size() - 1))];
        for (int customerId : customers) {
            customerScores.push_back({customerId, static_cast<float>(instance.distanceMatrix[anchorCustomer][customerId])});
        }
    } else if (strategy_choice == 4) { 
        for (int customerId : customers) {
            float sumDistToOthers = 0.0f;
            int countOthers = 0;
            if (customers.size() > 1) {
                for (int otherCustomerId : customers) {
                    if (customerId != otherCustomerId) {
                        sumDistToOthers += instance.distanceMatrix[customerId][otherCustomerId];
                        countOthers++;
                    }
                }
            }
            float score = 0.0f;
            if (countOthers > 0) {
                score = 1.0f / (1.0f + sumDistToOthers / countOthers); 
            }
            customerScores.push_back({customerId, score});
        }
    } else if (strategy_choice == 5) { 
        float alpha = getRandomFractionFast();
        for (int customerId : customers) {
            float normalized_distance = (max_dist_to_depot_subset > 0) ? static_cast<float>(instance.distanceMatrix[0][customerId]) / max_dist_to_depot_subset : 0.0f;
            float normalized_demand = (max_demand_subset > 0) ? static_cast<float>(instance.demand[customerId]) / max_demand_subset : 0.0f;
            
            float combined_score = alpha * normalized_distance + (1.0f - alpha) * normalized_demand;
            customerScores.push_back({customerId, combined_score});
        }
    } else if (strategy_choice == 6) { 
        for (int customerId : customers) {
            customerScores.push_back({customerId, 1.0f / (1.0f + static_cast<float>(instance.distanceMatrix[0][customerId]))});
        }
    } else if (strategy_choice == 7) { 
        int anchorCustomer = customers[getRandomNumber(0, static_cast<int>(customers.size() - 1))];
        for (int customerId : customers) {
            float score = 0.0f;
            if (customerId == anchorCustomer) {
                score = 1000.0f + getRandomFractionFast();
            } else {
                score = 1.0f / (1.0f + static_cast<float>(instance.distanceMatrix[anchorCustomer][customerId]));
            }
            customerScores.push_back({customerId, score});
        }
    }

    for (auto& cs : customerScores) {
        cs.score += (getRandomFractionFast() - 0.5f) * (cs.score * 0.05f);
    }

    if (sort_ascending) {
        std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
            return a.score < b.score;
        });
    } else {
        std::sort(customerScores.begin(), customerScores.end(), [](const auto& a, const auto& b) {
            return a.score > b.score;
        });
    }

    for (size_t i = 0; i + 1 < customerScores.size(); ++i) {
        if (getRandomFractionFast() < 0.12f) {
            std::swap(customerScores[i], customerScores[i+1]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].id;
    }
}