#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include <cmath>

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> frontier;

    int numCustomers = sol.instance.numCustomers;
    if (numCustomers == 0) {
        return {};
    }

    int min_remove_count = std::max(5, static_cast<int>(0.005 * numCustomers));
    int max_remove_count = std::min(25, static_cast<int>(0.03 * numCustomers));
    
    if (min_remove_count > max_remove_count) {
        min_remove_count = max_remove_count;
    }

    int numCustomersToRemove = getRandomNumber(min_remove_count, max_remove_count);

    if (numCustomersToRemove == 0) {
        return {};
    }

    selectedCustomersSet.reserve(static_cast<size_t>(numCustomersToRemove) + 5);
    frontier.reserve(static_cast<size_t>(numCustomersToRemove));

    int startCustomer = -1;
    const int MAX_SEED_SELECTION_ATTEMPTS = 55; 
    const float FOCUS_ON_VISITED_PROB_INITIAL_SEED = 0.65f + getRandomFractionFast() * 0.08f; 

    if (getRandomFractionFast() < FOCUS_ON_VISITED_PROB_INITIAL_SEED) {
        for (int i = 0; i < MAX_SEED_SELECTION_ATTEMPTS; ++i) {
            int candidateCustomer = getRandomNumber(1, numCustomers);
            if (sol.customerToTourMap[candidateCustomer] != -1) { 
                startCustomer = candidateCustomer;
                break;
            }
        }
    }
    if (startCustomer == -1) { 
        startCustomer = getRandomNumber(1, numCustomers);
    }
    
    selectedCustomersSet.insert(startCustomer);
    frontier.push_back(startCustomer);

    const int MAX_EXPANSION_ATTEMPTS = 500;
    int attempts = 0;

    const float PROB_PREFER_VISITED_NEW_SEED = 0.67f + getRandomFractionFast() * 0.09f;

    while (selectedCustomersSet.size() < static_cast<size_t>(numCustomersToRemove) && attempts < MAX_EXPANSION_ATTEMPTS) {
        if (frontier.empty()) { 
            int newSeed = -1;
            
            if (getRandomFractionFast() < PROB_PREFER_VISITED_NEW_SEED) {
                for (int i = 0; i < MAX_SEED_SELECTION_ATTEMPTS; ++i) {
                    int candidateCustomer = getRandomNumber(1, numCustomers);
                    if (sol.customerToTourMap[candidateCustomer] != -1 && selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
                        newSeed = candidateCustomer;
                        break;
                    }
                }
            }
            
            if (newSeed == -1) { 
                 for (int i = 0; i < MAX_SEED_SELECTION_ATTEMPTS; ++i) {
                    int candidateCustomer = getRandomNumber(1, numCustomers);
                    if (selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
                        newSeed = candidateCustomer;
                        break;
                    }
                }
            }

            if (newSeed != -1) { 
                selectedCustomersSet.insert(newSeed);
                frontier.push_back(newSeed);
            } else if (frontier.empty() && selectedCustomersSet.size() < static_cast<size_t>(numCustomersToRemove)) { 
                int fallbackSeed = -1;
                for(int i = 0; i < MAX_SEED_SELECTION_ATTEMPTS; ++i) {
                    int candidateCustomer = getRandomNumber(1, numCustomers);
                    if (selectedCustomersSet.find(candidateCustomer) == selectedCustomersSet.end()) {
                        fallbackSeed = candidateCustomer;
                        break;
                    }
                }
                if (fallbackSeed != -1) {
                    selectedCustomersSet.insert(fallbackSeed);
                    frontier.push_back(fallbackSeed);
                } else {
                    break; 
                }
            } else {
                break; 
            }
        }

        if (selectedCustomersSet.size() >= static_cast<size_t>(numCustomersToRemove) || frontier.empty()) {
            break; 
        }

        int expandFromIdx = getRandomNumber(0, static_cast<int>(frontier.size()) - 1);
        int currentCustomer = frontier[expandFromIdx];

        frontier[expandFromIdx] = frontier.back();
        frontier.pop_back();

        float expansion_strategy_roll = getRandomFractionFast();
        if (sol.customerToTourMap[currentCustomer] != -1 && 
            sol.customerToTourMap[currentCustomer] < sol.tours.size() && 
            expansion_strategy_roll < (0.55f + getRandomFractionFast() * 0.15f)) { 
            
            int tour_idx = sol.customerToTourMap[currentCustomer];
            const Tour& tour = sol.tours[tour_idx];
            
            int current_cust_pos_in_tour = -1;
            for (size_t k = 0; k < tour.customers.size(); ++k) {
                if (tour.customers[k] == currentCustomer) {
                    current_cust_pos_in_tour = static_cast<int>(k);
                    break;
                }
            }

            if (current_cust_pos_in_tour != -1) {
                if (current_cust_pos_in_tour + 1 < tour.customers.size()) {
                    int neighbor_in_tour = tour.customers[current_cust_pos_in_tour + 1];
                    if (neighbor_in_tour != 0 && selectedCustomersSet.find(neighbor_in_tour) == selectedCustomersSet.end()) {
                        selectedCustomersSet.insert(neighbor_in_tour);
                        frontier.push_back(neighbor_in_tour);
                        if (selectedCustomersSet.size() >= static_cast<size_t>(numCustomersToRemove)) break;
                    }
                }
                if (current_cust_pos_in_tour - 1 >= 0) {
                    int neighbor_in_tour = tour.customers[current_cust_pos_in_tour - 1];
                    if (neighbor_in_tour != 0 && selectedCustomersSet.find(neighbor_in_tour) == selectedCustomersSet.end()) {
                        selectedCustomersSet.insert(neighbor_in_tour);
                        frontier.push_back(neighbor_in_tour);
                        if (selectedCustomersSet.size() >= static_cast<size_t>(numCustomersToRemove)) break;
                    }
                }
                
                if (tour.customers.size() > 2 && getRandomFractionFast() < 0.62f) { 
                    int num_to_add_from_tour = getRandomNumber(0, std::min(4, static_cast<int>(tour.customers.size()) - 2));
                    for(int k=0; k < num_to_add_from_tour; ++k) {
                        int random_idx_in_tour = getRandomNumber(0, static_cast<int>(tour.customers.size()) - 1);
                        int random_cust_in_tour = tour.customers[random_idx_in_tour];
                        if (random_cust_in_tour != 0 && selectedCustomersSet.find(random_cust_in_tour) == selectedCustomersSet.end()) {
                            selectedCustomersSet.insert(random_cust_in_tour);
                            frontier.push_back(random_cust_in_tour);
                            if (selectedCustomersSet.size() >= static_cast<size_t>(numCustomersToRemove)) break; 
                        }
                    }
                }
            }
        } else {
            int numNeighborsToConsider = std::min(static_cast<int>(sol.instance.adj[currentCustomer].size()), 8 + getRandomNumber(0, 9));
            float prob_to_add = 0.68f + getRandomFractionFast() * 0.22f;

            for (int i = 0; i < numNeighborsToConsider; ++i) {
                int neighbor = sol.instance.adj[currentCustomer][i];

                if (neighbor == 0) continue; 

                if (selectedCustomersSet.size() >= static_cast<size_t>(numCustomersToRemove)) {
                    break;
                }
                
                if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                    if (getRandomFractionFast() < prob_to_add) {
                        selectedCustomersSet.insert(neighbor);
                        frontier.push_back(neighbor);
                    }
                }
            }
        }
        attempts++;
    }

    const int FINAL_FILL_ATTEMPTS = 50; 
    int fillAttempts = 0;
    while (selectedCustomersSet.size() < static_cast<size_t>(numCustomersToRemove) && fillAttempts < FINAL_FILL_ATTEMPTS) {
        int newCustomer = getRandomNumber(1, numCustomers);
        if (selectedCustomersSet.find(newCustomer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(newCustomer);
        }
        fillAttempts++;
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.size() <= 1) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    float rand_choice = getRandomFractionFast();

    if (rand_choice < 0.80f) { 
        float prize_dist_ratio_weight = 0.77f + getRandomFractionFast() * 0.43f;
        float prize_dist_weight_mult = 1.01f + getRandomFractionFast() * 0.23f; 
        float prize_demand_ratio_weight = 0.47f + getRandomFractionFast() * 0.33f;
        float prize_bonus_for_zero_demand_factor = 0.013f + getRandomFractionFast() * 0.027f;
        float demand_penalty_factor = 0.0415f + getRandomFractionFast() * 0.039f;
        float distance_penalty_factor = 0.00315f + getRandomFractionFast() * 0.00285f;
        float adj_size_bonus_weight = 0.019f + getRandomFractionFast() * 0.023f;
        float stochastic_noise_magnitude = 4.7f + getRandomFractionFast() * 12.3f;

        bool apply_capacity_fit_bonus = (instance.vehicleCapacity > 0 && getRandomFractionFast() < (0.29f + getRandomFractionFast() * 0.12f)); 
        float capacity_fit_bonus_weight = 0.008f + getRandomFractionFast() * 0.0215f;

        bool use_connectivity_bonus_within_set = (getRandomFractionFast() < 0.26f + getRandomFractionFast() * 0.06f); 
        float connectivity_bonus_magnitude = 0.0f;
        std::vector<bool> is_in_removed_set;

        if (use_connectivity_bonus_within_set) {
            connectivity_bonus_magnitude = 3.0f + getRandomFractionFast() * 5.0f;
            is_in_removed_set.resize(static_cast<size_t>(instance.numCustomers) + 1, false);
            for (int cust_id : customers) {
                if (cust_id >= 1 && cust_id <= instance.numCustomers) {
                    is_in_removed_set[cust_id] = true;
                }
            }
        }

        bool use_proximity_bonus = (getRandomFractionFast() < 0.19f + getRandomFractionFast() * 0.055f);
        float coeff_proximity_bonus = 0.0f; 
        int k_closest_neighbors_for_score = 0;
        if (use_proximity_bonus) {
            coeff_proximity_bonus = 0.0095f + getRandomFractionFast() * 0.019f;
            k_closest_neighbors_for_score = getRandomNumber(3, 8);
        }

        for (int customer_id : customers) {
            float score = 0.0f;
            float prize = static_cast<float>(instance.prizes[customer_id]);
            float demand = static_cast<float>(instance.demand[customer_id]);
            float distance_to_depot = static_cast<float>(instance.distanceMatrix[0][customer_id]);
            float adj_size = static_cast<float>(instance.adj[customer_id].size());

            score += ((prize / (distance_to_depot + 1.0f)) * prize_dist_ratio_weight) * prize_dist_weight_mult;
            
            if (demand > 0) {
                score += (prize / demand) * prize_demand_ratio_weight;
            } else {
                score += prize * prize_bonus_for_zero_demand_factor;
            }
            
            score -= demand * demand_penalty_factor;
            score -= distance_to_depot * distance_penalty_factor;
            score += adj_size * adj_size_bonus_weight;

            if (apply_capacity_fit_bonus) {
                if (demand > 0 && instance.vehicleCapacity > 0) {
                    score += (1.0f - demand / static_cast<float>(instance.vehicleCapacity)) * capacity_fit_bonus_weight;
                } else if (demand == 0 && instance.vehicleCapacity > 0) {
                    score += 1.0f * capacity_fit_bonus_weight;
                }
            }

            if (use_connectivity_bonus_within_set) {
                float connectivity_count = 0.0f;
                const int NEIGHBOR_CHECK_LIMIT = std::min(static_cast<int>(instance.adj[customer_id].size()), 6 + getRandomNumber(0, 5)); 
                for (int i = 0; i < NEIGHBOR_CHECK_LIMIT; ++i) {
                    int neighbor_id = instance.adj[customer_id][i];
                    if (neighbor_id == 0 || static_cast<size_t>(neighbor_id) > static_cast<size_t>(instance.numCustomers)) continue; 
                    if (is_in_removed_set[neighbor_id]) {
                        connectivity_count += 1.0f;
                    }
                }
                score += connectivity_count * connectivity_bonus_magnitude;
            }

            if (use_proximity_bonus && !instance.adj[customer_id].empty() && k_closest_neighbors_for_score > 0) {
                float sum_dist_to_neighbors = 0.0f;
                int num_considered_for_avg = 0;
                for (size_t j = 0; j < static_cast<size_t>(k_closest_neighbors_for_score) && j < instance.adj[customer_id].size(); ++j) {
                    int neighbor = instance.adj[customer_id][j];
                    if (neighbor == 0) continue; 
                    sum_dist_to_neighbors += static_cast<float>(instance.distanceMatrix[customer_id][neighbor]);
                    num_considered_for_avg++;
                }
                if (num_considered_for_avg > 0) {
                    score += (1.0f / (sum_dist_to_neighbors / static_cast<float>(num_considered_for_avg) + 1.0f)) * coeff_proximity_bonus;
                }
            }

            score += stochastic_noise_magnitude * (getRandomFractionFast() * 2.0f - 1.0f);

            score *= (1.0f + getRandomFractionFast() * 0.19f - 0.095f);

            scoredCustomers.push_back({score, customer_id});
        }
    } else if (rand_choice < 0.90f) { 
        for (int c : customers) {
            float score = static_cast<float>(instance.distanceMatrix[0][c]);
            score += getRandomFractionFast() * 0.002f - 0.001f; 
            scoredCustomers.push_back({score, c});
        }
        std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
            return a.first < b.first;
        });
    } else { 
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
        return; 
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}