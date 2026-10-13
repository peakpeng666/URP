#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <cmath>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<bool> is_selected_arr(sol.instance.numCustomers + 1, false);
    std::vector<bool> in_candidate_pool_arr(sol.instance.numCustomers + 1, false);

    std::vector<int> candidatePool_list;
    std::vector<int> result_selected_customers;

    int numCustomersToRemove = getRandomNumber(10, 20);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        return {};
    }

    result_selected_customers.reserve(static_cast<size_t>(numCustomersToRemove)); 
    candidatePool_list.reserve(static_cast<size_t>(numCustomersToRemove * 3)); 

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    is_selected_arr[initialCustomer] = true;
    result_selected_customers.push_back(initialCustomer);

    const int NEIGHBORS_TO_CONSIDER_FROM_ADJ_MIN = 10;
    const int NEIGHBORS_TO_CONSIDER_FROM_ADJ_MAX = 25;
    const int MAX_NEIGHBORS_TO_ACTUALLY_ADD_MIN = 2;
    const int MAX_NEIGHBORS_TO_ACTUALLY_ADD_MAX = 5;
    const int PROB_ADD_NEIGHBOR_TO_POOL_PERCENT = 87; 

    auto add_neighbors_to_pool = [&](int customer_id) {
        int neighbors_added_count = 0;
        int neighbors_to_scan_limit = getRandomNumber(NEIGHBORS_TO_CONSIDER_FROM_ADJ_MIN, NEIGHBORS_TO_CONSIDER_FROM_ADJ_MAX);
        neighbors_to_scan_limit = std::min(neighbors_to_scan_limit, static_cast<int>(sol.instance.adj[customer_id].size()));
        
        int max_neighbors_to_actually_add = getRandomNumber(MAX_NEIGHBORS_TO_ACTUALLY_ADD_MIN, MAX_NEIGHBORS_TO_ACTUALLY_ADD_MAX);

        for (int i = 0; i < neighbors_to_scan_limit; ++i) {
            int neighbor = sol.instance.adj[customer_id][i];
            if (neighbor == 0 || neighbor > sol.instance.numCustomers) continue; 

            if (!is_selected_arr[neighbor] && !in_candidate_pool_arr[neighbor]) {
                if (getRandomNumber(0, 99) < PROB_ADD_NEIGHBOR_TO_POOL_PERCENT) { 
                    candidatePool_list.push_back(neighbor);
                    in_candidate_pool_arr[neighbor] = true;
                    neighbors_added_count++;
                    if (neighbors_added_count >= max_neighbors_to_actually_add) {
                        break; 
                    }
                }
            }
        }
    };

    add_neighbors_to_pool(initialCustomer);

    while (static_cast<int>(result_selected_customers.size()) < numCustomersToRemove) {
        if (candidatePool_list.empty()) {
            int fallbackCustomer = -1;
            for (int attempts = 0; attempts < 100; ++attempts) {
                 int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                 if (!is_selected_arr[rand_cust]) {
                     fallbackCustomer = rand_cust;
                     break;
                 }
            }
            
            if (fallbackCustomer == -1) { 
                for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                    if (!is_selected_arr[i]) {
                        fallbackCustomer = i;
                        break;
                    }
                }
            }

            if (fallbackCustomer != -1) {
                is_selected_arr[fallbackCustomer] = true;
                result_selected_customers.push_back(fallbackCustomer);
                add_neighbors_to_pool(fallbackCustomer);
            } else {
                break; 
            }

            if (static_cast<int>(result_selected_customers.size()) == numCustomersToRemove) {
                 break;
            }
            continue;
        }

        int rand_idx = getRandomNumber(0, static_cast<int>(candidatePool_list.size()) - 1);
        int customerToAdd = candidatePool_list[rand_idx];

        is_selected_arr[customerToAdd] = true;
        result_selected_customers.push_back(customerToAdd);

        candidatePool_list[rand_idx] = candidatePool_list.back();
        candidatePool_list.pop_back();
        in_candidate_pool_arr[customerToAdd] = false;

        add_neighbors_to_pool(customerToAdd);
    }

    return result_selected_customers;
}

struct CustomerSortData {
    int customerId;
    float primary_val;
    float secondary_val;
    float tertiary_val;

    bool operator<(const CustomerSortData& other) const {
        if (primary_val != other.primary_val) {
            return primary_val < other.primary_val;
        }
        if (secondary_val != other.secondary_val) {
            return secondary_val < other.secondary_val;
        }
        if (tertiary_val != other.tertiary_val) {
            return tertiary_val < other.tertiary_val;
        }
        return customerId < other.customerId;
    }
};

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());
    static thread_local std::uniform_real_distribution<float> dist_uniform(0.0f, 1.0f);

    float choice = dist_uniform(gen);
    
    std::vector<CustomerSortData> sort_data_vec;
    sort_data_vec.reserve(customers.size());

    const float P_TW_WIDTH_DEMAND_SERVICE = 0.28f; 
    const float P_DIST_DEPOT = 0.17f;
    const float P_START_TW = 0.13f;
    const float P_DEMAND = 0.09f;
    const float P_NEIGHBORS = 0.07f;
    const float P_SUM_DIST_TO_OTHERS = 0.04f;
    const float P_END_TW_PLUS_SERVICE = 0.06f;
    const float P_CUSTOM_SCORE_1 = 0.05f;
    const float P_SHUFFLE = 0.05f;
    const float P_COMPOSITE_SCORE = 0.05f; 
    
    float cumulative_prob = 0.0f;

    cumulative_prob += P_TW_WIDTH_DEMAND_SERVICE;
    if (choice < cumulative_prob) { 
        const float RANDOM_NOISE_SCALE = 0.0001f; 
        for (int customerId : customers) {
            sort_data_vec.push_back({
                customerId,
                instance.TW_Width[customerId] + dist_uniform(gen) * RANDOM_NOISE_SCALE,
                static_cast<float>(-instance.demand[customerId]),
                static_cast<float>(-instance.serviceTime[customerId])
            });
        }
    } else {
        cumulative_prob += P_DIST_DEPOT;
        if (choice < cumulative_prob) { 
            for (int customerId : customers) {
                sort_data_vec.push_back({customerId, -instance.distanceMatrix[0][customerId], dist_uniform(gen), dist_uniform(gen)});
            }
        } else {
            cumulative_prob += P_START_TW;
            if (choice < cumulative_prob) { 
                for (int customerId : customers) {
                    sort_data_vec.push_back({customerId, static_cast<float>(instance.startTW[customerId]), dist_uniform(gen), dist_uniform(gen)});
                }
            } else {
                cumulative_prob += P_DEMAND;
                if (choice < cumulative_prob) { 
                    for (int customerId : customers) {
                        sort_data_vec.push_back({customerId, static_cast<float>(-instance.demand[customerId]), dist_uniform(gen), dist_uniform(gen)});
                    }
                } else {
                    cumulative_prob += P_NEIGHBORS;
                    if (choice < cumulative_prob) { 
                        bool sort_ascending_neighbors = (dist_uniform(gen) < 0.5f);
                        for (int customerId : customers) {
                            float val = static_cast<float>(instance.adj[customerId].size());
                            sort_data_vec.push_back({customerId, (sort_ascending_neighbors ? val : -val), dist_uniform(gen), dist_uniform(gen)});
                        }
                    } else {
                        cumulative_prob += P_SUM_DIST_TO_OTHERS;
                        if (choice < cumulative_prob) { 
                            std::vector<double> sum_dists(instance.numCustomers + 1, 0.0);
                            for (size_t i = 0; i < customers.size(); ++i) {
                                for (size_t j = i + 1; j < customers.size(); ++j) {
                                    int id1 = customers[i];
                                    int id2 = customers[j];
                                    double dist = instance.distanceMatrix[id1][id2];
                                    sum_dists[id1] += dist;
                                    sum_dists[id2] += dist;
                                }
                            }
                            for (int customerId : customers) {
                                sort_data_vec.push_back({customerId, static_cast<float>(sum_dists[customerId]), dist_uniform(gen), dist_uniform(gen)});
                            }
                        } else {
                            cumulative_prob += P_END_TW_PLUS_SERVICE;
                            if (choice < cumulative_prob) { 
                                for (int customerId : customers) {
                                    float end_tw_plus_service = instance.startTW[customerId] + instance.TW_Width[customerId] + instance.serviceTime[customerId];
                                    sort_data_vec.push_back({customerId, -end_tw_plus_service, dist_uniform(gen), dist_uniform(gen)});
                                }
                            } else {
                                cumulative_prob += P_CUSTOM_SCORE_1;
                                if (choice < cumulative_prob) {
                                    for (int customerId : customers) {
                                        float score = (instance.TW_Width[customerId] * 0.5f + instance.serviceTime[customerId] * 0.5f) / (static_cast<float>(instance.demand[customerId]) + 1.0f);
                                        sort_data_vec.push_back({customerId, score, dist_uniform(gen), dist_uniform(gen)});
                                    }
                                } else {
                                    cumulative_prob += P_SHUFFLE;
                                    if (choice < cumulative_prob) { 
                                        std::shuffle(customers.begin(), customers.end(), gen);
                                        return;
                                    } else { 
                                        cumulative_prob += P_COMPOSITE_SCORE;
                                        if (choice < cumulative_prob) {
                                            const float W_TW_WIDTH_INV = 3.4f;
                                            const float W_START_TW_INV = 2.4f;
                                            const float W_SERVICE = 1.15f;
                                            const float W_DEMAND = 1.75f;
                                            const float W_DIST_DEPOT = 0.65f;
                                            const float W_END_TW = 0.25f;
                                            const float W_ADJ_SIZE = 0.15f;

                                            for (int customerId : customers) {
                                                float score = 0.0f;
                                                score += W_TW_WIDTH_INV / (instance.TW_Width[customerId] + 0.01f);
                                                score += W_START_TW_INV / (static_cast<float>(instance.startTW[customerId]) + 1.0f);
                                                score += W_SERVICE * static_cast<float>(instance.serviceTime[customerId]);
                                                score += W_DEMAND * static_cast<float>(instance.demand[customerId]);
                                                score += W_DIST_DEPOT * static_cast<float>(instance.distanceMatrix[0][customerId]);
                                                score += W_END_TW * (static_cast<float>(instance.startTW[customerId]) + instance.TW_Width[customerId]);
                                                score += W_ADJ_SIZE * static_cast<float>(instance.adj[customerId].size());

                                                sort_data_vec.push_back({customerId, -score, dist_uniform(gen), dist_uniform(gen)});
                                            }
                                        } else { 
                                            for (int customerId : customers) {
                                                float score = (static_cast<float>(instance.demand[customerId])) / (static_cast<float>(instance.serviceTime[customerId]) + 1.0f);
                                                sort_data_vec.push_back({customerId, -score, dist_uniform(gen), dist_uniform(gen)});
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    std::sort(sort_data_vec.begin(), sort_data_vec.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data_vec[i].customerId;
    }
}