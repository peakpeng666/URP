#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <limits>
#include <utility>
#include <numeric>

#include "Utils.h"

static thread_local std::mt19937 rng(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<bool> is_selected(sol.instance.numCustomers + 1, false);
    std::vector<int> selected_customers_list;
    std::vector<int> potential_seeds;

    int numCustomersToRemove = getRandomNumber(10, 25);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    is_selected[initialSeedCustomer] = true;
    selected_customers_list.push_back(initialSeedCustomer);
    potential_seeds.push_back(initialSeedCustomer);

    int neighborsToConsider = getRandomNumber(15, 30);
    float baseSelectionProbability = 0.7f + getRandomFractionFast() * 0.2f; // 0.7 to 0.9

    float demandInfluenceFactor = 0.05f + getRandomFractionFast() * 0.10f; // 0.05 to 0.15
    float effectiveVehicleCapacity = static_cast<float>(sol.instance.vehicleCapacity);
    if (effectiveVehicleCapacity < 1.0f) effectiveVehicleCapacity = 1.0f;

    int max_attempts_without_progress = 5;
    int attempts_without_progress = 0;

    while (selected_customers_list.size() < static_cast<size_t>(numCustomersToRemove)) {
        bool added_customer_this_iteration = false;

        if (!potential_seeds.empty()) {
            int currentSeedIdxInVector = getRandomNumber(0, static_cast<int>(potential_seeds.size() - 1));
            int currentSeedCustomer = potential_seeds[currentSeedIdxInVector];
            
            std::swap(potential_seeds[currentSeedIdxInVector], potential_seeds.back());
            potential_seeds.pop_back();

            int num_adj_neighbors = sol.instance.adj[currentSeedCustomer].size();
            for (int i = 0; i < num_adj_neighbors && i < neighborsToConsider; ++i) {
                int neighborCustomer = sol.instance.adj[currentSeedCustomer][i];
                
                if (neighborCustomer == 0 || neighborCustomer > sol.instance.numCustomers || is_selected[neighborCustomer]) {
                    continue;
                }

                float normalizedDemand = static_cast<float>(sol.instance.demand[neighborCustomer]) / effectiveVehicleCapacity;
                normalizedDemand = std::min(1.0f, normalizedDemand); 
                
                float selectionProbability = baseSelectionProbability * (1.0f + normalizedDemand * demandInfluenceFactor);
                selectionProbability = std::min(1.0f, selectionProbability);

                if (getRandomFractionFast() < selectionProbability) {
                    is_selected[neighborCustomer] = true;
                    selected_customers_list.push_back(neighborCustomer);
                    potential_seeds.push_back(neighborCustomer);
                    added_customer_this_iteration = true;
                    if (selected_customers_list.size() >= static_cast<size_t>(numCustomersToRemove)) {
                        break;
                    }
                }
            }
        }
        
        if (!added_customer_this_iteration && selected_customers_list.size() < static_cast<size_t>(numCustomersToRemove)) {
            attempts_without_progress++;

            bool jumped_successfully = false;
            if (getRandomFractionFast() < 0.6f && !selected_customers_list.empty()) { 
                int attempts = 0;
                while (attempts < 5) {
                    int reseed_customer_idx = getRandomNumber(0, static_cast<int>(selected_customers_list.size() - 1));
                    int reseed_from_customer = selected_customers_list[reseed_customer_idx];

                    std::vector<int> unselected_neighbors;
                    for (int neighbor_id : sol.instance.adj[reseed_from_customer]) {
                        if (neighbor_id != 0 && neighbor_id <= sol.instance.numCustomers && !is_selected[neighbor_id]) {
                            unselected_neighbors.push_back(neighbor_id);
                        }
                    }

                    if (!unselected_neighbors.empty()) {
                        int candidate_to_add = unselected_neighbors[getRandomNumber(0, static_cast<int>(unselected_neighbors.size() - 1))];
                        is_selected[candidate_to_add] = true;
                        selected_customers_list.push_back(candidate_to_add);
                        potential_seeds.push_back(candidate_to_add);
                        jumped_successfully = true;
                        added_customer_this_iteration = true;
                        break;
                    }
                    attempts++;
                }
            }

            if (!jumped_successfully && selected_customers_list.size() < static_cast<size_t>(numCustomersToRemove)) {
                int fallback_customer = -1;
                for (int i = 0; i < 10; ++i) {
                    int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                    if (!is_selected[rand_cust]) {
                        fallback_customer = rand_cust;
                        break;
                    }
                }
                if (fallback_customer != -1) {
                    is_selected[fallback_customer] = true;
                    selected_customers_list.push_back(fallback_customer);
                    potential_seeds.push_back(fallback_customer);
                    added_customer_this_iteration = true;
                }
            }
        }

        if (!added_customer_this_iteration && attempts_without_progress >= max_attempts_without_progress) {
            break; 
        } else if (added_customer_this_iteration) {
            attempts_without_progress = 0;
        }
    }

    return selected_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int choice = getRandomNumber(0, 99); 

    float noise_magnitude_factor = 0.03f + getRandomFractionFast() * 0.05f;

    if (choice < 55) { 
        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size());

        int reference_customer_id = 0;
        if (customers.size() > 1 && getRandomFractionFast() < 0.4f) {
            reference_customer_id = customers[getRandomNumber(0, static_cast<int>(customers.size() - 1))];
        }

        float weight_dist_depot = getRandomFractionFast() * 2.0f;
        float weight_dist_ref = getRandomFractionFast() * 2.0f;
        float weight_demand = getRandomFractionFast() * 2.0f;
        
        if (weight_dist_depot + weight_dist_ref + weight_demand < 0.1f) {
            weight_dist_depot = 1.0f;
        }

        float max_demand_val = static_cast<float>(instance.vehicleCapacity > 0 ? instance.vehicleCapacity : 1.0f);
        
        float max_dist_depot_val = 0.0f;
        float max_dist_ref_val = 0.0f;
        for (int customer_id : customers) {
            if (static_cast<float>(instance.distanceMatrix[0][customer_id]) > max_dist_depot_val) {
                max_dist_depot_val = static_cast<float>(instance.distanceMatrix[0][customer_id]);
            }
            if (static_cast<float>(instance.distanceMatrix[reference_customer_id][customer_id]) > max_dist_ref_val) {
                max_dist_ref_val = static_cast<float>(instance.distanceMatrix[reference_customer_id][customer_id]);
            }
        }
        if (max_dist_depot_val == 0.0f) max_dist_depot_val = 1.0f;
        if (max_dist_ref_val == 0.0f) max_dist_ref_val = 1.0f;

        for (int customer_id : customers) {
            float normalized_dist_to_depot = static_cast<float>(instance.distanceMatrix[0][customer_id]) / max_dist_depot_val;
            float normalized_dist_to_ref = static_cast<float>(instance.distanceMatrix[reference_customer_id][customer_id]) / max_dist_ref_val;
            float normalized_demand = static_cast<float>(instance.demand[customer_id]) / max_demand_val;
            
            float score = weight_dist_depot * normalized_dist_to_depot +
                          weight_dist_ref * normalized_dist_to_ref +
                          weight_demand * normalized_demand;
            
            float noise = (getRandomFractionFast() * 2.0f - 1.0f) * score * noise_magnitude_factor;
            score += noise;
            customer_scores.emplace_back(score, customer_id);
        }

        bool sort_ascending = getRandomFractionFast() < 0.5f; 
        if (sort_ascending) {
            std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
                return a.first < b.first;
            });
        } else {
            std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
                return a.first > b.first;
            });
        }

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }

    } else if (choice < 80) { 
        std::vector<std::pair<float, int>> customer_distances;
        customer_distances.reserve(customers.size());

        int pivot_customer_idx = getRandomNumber(0, static_cast<int>(customers.size() - 1));
        int pivot_customer_id = customers[pivot_customer_idx];
        
        for (int customer_id : customers) {
            float base_dist = static_cast<float>(instance.distanceMatrix[pivot_customer_id][customer_id]);
            float noise = (getRandomFractionFast() * 2.0f - 1.0f) * base_dist * noise_magnitude_factor;
            float noisy_dist = base_dist + noise;
            customer_distances.emplace_back(noisy_dist, customer_id);
        }

        bool sort_ascending = getRandomFractionFast() < 0.5f; 
        if (sort_ascending) {
            std::sort(customer_distances.begin(), customer_distances.end(), [](const auto& a, const auto& b) {
                return a.first < b.first;
            });
        } else {
            std::sort(customer_distances.begin(), customer_distances.end(), [](const auto& a, const auto& b) {
                return a.first > b.first;
            });
        }

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_distances[i].second;
        }

    } else if (choice < 95) { 
        std::vector<std::pair<float, int>> scores_and_customers;
        scores_and_customers.reserve(customers.size());

        int sort_metric_choice = getRandomNumber(0, 3); // Added one more option

        if (sort_metric_choice == 0) { 
            for (int customer_id : customers) {
                float base_score = static_cast<float>(instance.demand[customer_id]);
                float noise = (getRandomFractionFast() * 2.0f - 1.0f) * base_score * noise_magnitude_factor;
                scores_and_customers.push_back({base_score + noise, customer_id});
            }
        } else if (sort_metric_choice == 1) { 
            for (int customer_id : customers) {
                float base_score = static_cast<float>(instance.distanceMatrix[0][customer_id]);
                float noise = (getRandomFractionFast() * 2.0f - 1.0f) * base_score * noise_magnitude_factor;
                scores_and_customers.push_back({base_score + noise, customer_id});
            }
        } else if (sort_metric_choice == 2) { // Demand/Distance ratio from Worse Code
            for (int customer_id : customers) {
                float demand_val = static_cast<float>(instance.demand[customer_id]);
                float dist_val = static_cast<float>(instance.distanceMatrix[0][customer_id]); 
                
                float score = 0.0f;
                if (dist_val > 0.01f) { 
                    score = demand_val / dist_val; 
                } else { 
                    score = demand_val * 1000.0f; 
                }
                
                float noise = (getRandomFractionFast() * 2.0f - 1.0f) * score * noise_magnitude_factor;
                scores_and_customers.push_back({score + noise, customer_id});
            }
        } else { 
            int random_ref_id = getRandomNumber(0, instance.numCustomers); 
            if (customers.size() > 1 && getRandomFractionFast() < 0.6f) { 
                 random_ref_id = customers[getRandomNumber(0, static_cast<int>(customers.size() - 1))];
            }
            for (int customer_id : customers) {
                float base_score = static_cast<float>(instance.distanceMatrix[random_ref_id][customer_id]);
                float noise = (getRandomFractionFast() * 2.0f - 1.0f) * base_score * noise_magnitude_factor;
                scores_and_customers.push_back({base_score + noise, customer_id});
            }
        }

        bool sortAscending = (getRandomFractionFast() < 0.5f); 
        if (sortAscending) {
            std::sort(scores_and_customers.begin(), scores_and_customers.end(), [](const auto& a, const auto& b) {
                return a.first < b.first;
            });
        } else {
            std::sort(scores_and_customers.begin(), scores_and_customers.end(), [](const auto& a, const auto& b) {
                return a.first > b.first;
            });
        }

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scores_and_customers[i].second;
        }
    } else { 
        std::shuffle(customers.begin(), customers.end(), rng);
    }

    if (!customers.empty()) {
        int num_swaps = getRandomNumber(0, std::min(static_cast<int>(customers.size() / 2), 3)); 
        for (int i = 0; i < num_swaps; ++i) {
            if (customers.size() < 2) break;
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            int idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            while (idx1 == idx2) { 
                idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            }
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}